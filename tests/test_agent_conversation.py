"""Tests for agent_conversation.py — state machine, event dispatch, autonomy gate."""

from __future__ import annotations

import tempfile
import threading
import unittest
from pathlib import Path

from system_coach_maintenance_manager import agent_conversation


def _yaml_path(content: str) -> Path:
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
    tmp.write(content)
    tmp.flush()
    return Path(tmp.name)


def _a1_path() -> Path:
    return _yaml_path("agent_autonomy_level: A1\nagent_depth_level: D1\n")


def _a0_path() -> Path:
    return _yaml_path("agent_autonomy_level: A0\nagent_depth_level: D1\n")


class TestStartSession(unittest.TestCase):
    def test_returns_unique_handles(self):
        h1 = agent_conversation.start_session()
        h2 = agent_conversation.start_session()
        self.assertNotEqual(h1, h2)

    def test_handle_has_expected_prefix(self):
        h = agent_conversation.start_session()
        self.assertTrue(h.startswith("conv-"))

    def test_reads_autonomy_and_depth_from_yaml(self):
        path = _yaml_path("agent_autonomy_level: A3\nagent_depth_level: D2\n")
        h = agent_conversation.start_session(project_control_path=path)
        info = agent_conversation.session_info(h)
        self.assertEqual(info["autonomy_level"], "A3")
        self.assertEqual(info["depth_level"], "D2")

    def test_nested_yaml_format_is_accepted(self):
        path = _yaml_path("agent_controls:\n  agent_autonomy_level: A2\n  agent_depth_level: D3\n")
        h = agent_conversation.start_session(project_control_path=path)
        info = agent_conversation.session_info(h)
        self.assertEqual(info["autonomy_level"], "A2")
        self.assertEqual(info["depth_level"], "D3")

    def test_missing_yaml_defaults_to_a0_d1(self):
        path = Path("/nonexistent/project-control.yaml")
        h = agent_conversation.start_session(project_control_path=path)
        info = agent_conversation.session_info(h)
        self.assertEqual(info["autonomy_level"], "A0")
        self.assertEqual(info["depth_level"], "D1")

    def test_initial_history_length_is_zero(self):
        h = agent_conversation.start_session()
        self.assertEqual(agent_conversation.session_info(h)["history_length"], 0)

    def test_initial_pending_action_is_none(self):
        h = agent_conversation.start_session()
        self.assertIsNone(agent_conversation.session_info(h)["pending_action"])


class TestSubmitMessage(unittest.TestCase):
    def setUp(self):
        self.handle = agent_conversation.start_session(project_control_path=_a1_path())
        self.events: list[tuple[str, dict]] = []
        agent_conversation.on_event(self.handle, lambda t, p: self.events.append((t, p)))

    def test_user_message_appended_to_history(self):
        agent_conversation.submit_message(self.handle, "hello")
        self.assertEqual(agent_conversation.session_info(self.handle)["history_length"], 1)

    def test_message_role_is_user(self):
        agent_conversation.submit_message(self.handle, "hello")
        session = agent_conversation._get_session(self.handle)
        self.assertEqual(session.history()[0]["role"], "user")

    def test_message_text_is_stripped(self):
        agent_conversation.submit_message(self.handle, "  hello  ")
        session = agent_conversation._get_session(self.handle)
        self.assertEqual(session.history()[0]["text"], "hello")

    def test_session_done_emitted_on_submit(self):
        agent_conversation.submit_message(self.handle, "hello")
        types = [t for t, _ in self.events]
        self.assertIn(agent_conversation.EVENT_SESSION_DONE, types)

    def test_session_done_payload_contains_message(self):
        agent_conversation.submit_message(self.handle, "hello")
        payload = next(p for t, p in self.events if t == agent_conversation.EVENT_SESSION_DONE)
        self.assertIn("message", payload)
        self.assertEqual(payload["message"]["text"], "hello")

    def test_empty_message_emits_error_not_done(self):
        agent_conversation.submit_message(self.handle, "   ")
        types = [t for t, _ in self.events]
        self.assertIn(agent_conversation.EVENT_ERROR, types)
        self.assertNotIn(agent_conversation.EVENT_SESSION_DONE, types)

    def test_empty_message_does_not_grow_history(self):
        agent_conversation.submit_message(self.handle, "")
        self.assertEqual(agent_conversation.session_info(self.handle)["history_length"], 0)

    def test_unknown_handle_raises_key_error(self):
        with self.assertRaises(KeyError):
            agent_conversation.submit_message("no-such-handle", "hi")


class TestOnEvent(unittest.TestCase):
    def test_unknown_handle_raises_key_error(self):
        with self.assertRaises(KeyError):
            agent_conversation.on_event("bad-handle", lambda t, p: None)

    def test_multiple_callbacks_all_invoked(self):
        h = agent_conversation.start_session(project_control_path=_a1_path())
        calls: list[str] = []
        agent_conversation.on_event(h, lambda t, p: calls.append("cb1"))
        agent_conversation.on_event(h, lambda t, p: calls.append("cb2"))
        agent_conversation.submit_message(h, "hi")
        self.assertIn("cb1", calls)
        self.assertIn("cb2", calls)

    def test_callback_receives_correct_event_type(self):
        h = agent_conversation.start_session(project_control_path=_a1_path())
        received: list[str] = []
        agent_conversation.on_event(h, lambda t, p: received.append(t))
        agent_conversation.submit_message(h, "hi")
        self.assertEqual(received[0], agent_conversation.EVENT_SESSION_DONE)


class TestEmitToken(unittest.TestCase):
    def test_agent_token_event_dispatched(self):
        h = agent_conversation.start_session(project_control_path=_a1_path())
        events: list[tuple[str, dict]] = []
        agent_conversation.on_event(h, lambda t, p: events.append((t, p)))
        agent_conversation.emit_token(h, "hello")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0][0], agent_conversation.EVENT_AGENT_TOKEN)
        self.assertEqual(events[0][1]["token"], "hello")

    def test_multiple_tokens_accumulate_in_buffer(self):
        h = agent_conversation.start_session(project_control_path=_a1_path())
        agent_conversation.emit_token(h, "foo")
        agent_conversation.emit_token(h, " bar")
        session = agent_conversation._get_session(h)
        self.assertEqual(session.flush_tokens(), "foo bar")

    def test_unknown_handle_raises_key_error(self):
        with self.assertRaises(KeyError):
            agent_conversation.emit_token("bad", "tok")


class TestProposeAction(unittest.TestCase):
    def test_a1_emits_action_proposed(self):
        h = agent_conversation.start_session(project_control_path=_a1_path())
        events: list[tuple[str, dict]] = []
        agent_conversation.on_event(h, lambda t, p: events.append((t, p)))
        agent_conversation.propose_action(h, {"id": "plan-x", "title": "Test"})
        types = [t for t, _ in events]
        self.assertIn(agent_conversation.EVENT_ACTION_PROPOSED, types)

    def test_a0_suppresses_action_proposed(self):
        h = agent_conversation.start_session(project_control_path=_a0_path())
        events: list[tuple[str, dict]] = []
        agent_conversation.on_event(h, lambda t, p: events.append((t, p)))
        agent_conversation.propose_action(h, {"id": "plan-x"})
        types = [t for t, _ in events]
        self.assertNotIn(agent_conversation.EVENT_ACTION_PROPOSED, types)

    def test_a0_emits_error_instead(self):
        h = agent_conversation.start_session(project_control_path=_a0_path())
        events: list[tuple[str, dict]] = []
        agent_conversation.on_event(h, lambda t, p: events.append((t, p)))
        agent_conversation.propose_action(h, {"id": "plan-x"})
        types = [t for t, _ in events]
        self.assertIn(agent_conversation.EVENT_ERROR, types)

    def test_a0_error_payload_includes_action_id(self):
        h = agent_conversation.start_session(project_control_path=_a0_path())
        events: list[tuple[str, dict]] = []
        agent_conversation.on_event(h, lambda t, p: events.append((t, p)))
        agent_conversation.propose_action(h, {"id": "plan-z"})
        payload = next(p for t, p in events if t == agent_conversation.EVENT_ERROR)
        self.assertEqual(payload["action_id"], "plan-z")

    def test_a1_sets_pending_action(self):
        h = agent_conversation.start_session(project_control_path=_a1_path())
        agent_conversation.propose_action(h, {"id": "plan-x"})
        self.assertIsNotNone(agent_conversation.session_info(h)["pending_action"])

    def test_a0_does_not_set_pending_action(self):
        h = agent_conversation.start_session(project_control_path=_a0_path())
        agent_conversation.propose_action(h, {"id": "plan-x"})
        self.assertIsNone(agent_conversation.session_info(h)["pending_action"])


class TestRecordActionResult(unittest.TestCase):
    def test_clears_pending_action(self):
        h = agent_conversation.start_session(project_control_path=_a1_path())
        agent_conversation.propose_action(h, {"id": "plan-x"})
        agent_conversation.record_action_result(h, {"status": "completed"})
        self.assertIsNone(agent_conversation.session_info(h)["pending_action"])

    def test_emits_action_result(self):
        h = agent_conversation.start_session(project_control_path=_a1_path())
        events: list[tuple[str, dict]] = []
        agent_conversation.on_event(h, lambda t, p: events.append((t, p)))
        agent_conversation.record_action_result(h, {"status": "completed"})
        types = [t for t, _ in events]
        self.assertIn(agent_conversation.EVENT_ACTION_RESULT, types)

    def test_result_payload_forwarded(self):
        h = agent_conversation.start_session(project_control_path=_a1_path())
        events: list[tuple[str, dict]] = []
        agent_conversation.on_event(h, lambda t, p: events.append((t, p)))
        agent_conversation.record_action_result(h, {"status": "blocked", "error": "x"})
        payload = next(p for t, p in events if t == agent_conversation.EVENT_ACTION_RESULT)
        self.assertEqual(payload["result"]["status"], "blocked")


class TestEndSession(unittest.TestCase):
    def test_session_removed_after_end(self):
        h = agent_conversation.start_session()
        agent_conversation.end_session(h)
        with self.assertRaises(KeyError):
            agent_conversation.session_info(h)

    def test_callbacks_removed_after_end(self):
        h = agent_conversation.start_session()
        agent_conversation.end_session(h)
        with self.assertRaises(KeyError):
            agent_conversation.on_event(h, lambda t, p: None)

    def test_end_unknown_handle_is_silent(self):
        agent_conversation.end_session("no-such-handle")


class TestConcurrentCallbackOrdering(unittest.TestCase):
    def test_concurrent_submits_all_reach_callback(self):
        h = agent_conversation.start_session(project_control_path=_a1_path())
        received: list[str] = []
        lock = threading.Lock()

        def cb(event_type: str, payload: dict) -> None:
            with lock:
                received.append(event_type)

        agent_conversation.on_event(h, cb)

        threads = [
            threading.Thread(target=agent_conversation.submit_message, args=(h, f"msg {i}"))
            for i in range(8)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        done_events = [e for e in received if e == agent_conversation.EVENT_SESSION_DONE]
        self.assertEqual(len(done_events), 8)


if __name__ == "__main__":
    unittest.main()
