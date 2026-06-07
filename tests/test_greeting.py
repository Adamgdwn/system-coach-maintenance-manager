"""Tests for Chunk 25: diagnostic greeting generator and launch function."""

from __future__ import annotations

import threading
import unittest

from system_coach_maintenance_manager import agent_conversation
from system_coach_maintenance_manager.agent_conversation import (
    GREETING_HEALTHY,
    GREETING_PARTIAL_FAILURE,
    generate_greeting,
    launch_diagnostic_greeting,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _healthy_report() -> dict:
    return {
        "findings": [
            {"id": "cpu-load", "severity": "info", "status": "ok", "title": "CPU Load"},
            {"id": "diagnostic-readiness", "severity": "info", "status": "ok", "title": "Diagnostic Readiness"},
        ],
        "metrics": {},
        "command_log": [],
        "generated_at": "2026-06-07T14:00:00",
    }


def _findings_report(*severities_and_ids: tuple[str, str, str]) -> dict:
    """Build a report whose findings have the given (id, severity, title) tuples."""
    return {
        "findings": [
            {"id": fid, "severity": sev, "status": sev, "title": title}
            for fid, sev, title in severities_and_ids
        ],
        "metrics": {},
        "command_log": [],
        "generated_at": "2026-06-07T14:00:00",
    }


def _wait_for_done(events: list, timeout: float = 2.0) -> bool:
    deadline = threading.Event()
    sentinel = threading.Event()

    def _check() -> None:
        import time
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            if any(e == agent_conversation.EVENT_SESSION_DONE for e, _ in events):
                sentinel.set()
                return
            time.sleep(0.01)
        sentinel.set()

    threading.Thread(target=_check, daemon=True).start()
    sentinel.wait(timeout + 0.5)
    return any(e == agent_conversation.EVENT_SESSION_DONE for e, _ in events)


# ---------------------------------------------------------------------------
# generate_greeting — pure function tests
# ---------------------------------------------------------------------------

class TestGenerateGreetingHealthy(unittest.TestCase):
    def test_empty_findings_list_is_healthy(self):
        report = {"findings": [], "generated_at": "2026-06-07T14:00:00"}
        self.assertEqual(generate_greeting(report), GREETING_HEALTHY)

    def test_all_info_findings_is_healthy(self):
        report = _healthy_report()
        self.assertEqual(generate_greeting(report), GREETING_HEALTHY)

    def test_ok_severity_is_healthy(self):
        report = _findings_report(("cpu-load", "ok", "CPU Load"))
        self.assertEqual(generate_greeting(report), GREETING_HEALTHY)


class TestGenerateGreetingPartialFailure(unittest.TestCase):
    def test_none_report_returns_partial_failure(self):
        self.assertEqual(generate_greeting(None), GREETING_PARTIAL_FAILURE)

    def test_empty_dict_returns_partial_failure(self):
        self.assertEqual(generate_greeting({}), GREETING_PARTIAL_FAILURE)

    def test_error_key_returns_partial_failure(self):
        self.assertEqual(generate_greeting({"error": "timed out"}), GREETING_PARTIAL_FAILURE)


class TestGenerateGreetingFindingsPresent(unittest.TestCase):
    def test_warning_finding_triggers_findings_state(self):
        report = _findings_report(("disk-/", "warning", "Disk Space: /"))
        greeting = generate_greeting(report)
        self.assertNotEqual(greeting, GREETING_HEALTHY)
        self.assertNotEqual(greeting, GREETING_PARTIAL_FAILURE)

    def test_critical_finding_triggers_findings_state(self):
        report = _findings_report(("memory-pressure", "critical", "Memory Pressure"))
        greeting = generate_greeting(report)
        self.assertNotIn("clean", greeting)

    def test_greeting_includes_finding_count(self):
        report = _findings_report(("disk-/", "warning", "Disk Space: /"))
        greeting = generate_greeting(report)
        self.assertIn("1", greeting)

    def test_greeting_includes_finding_title(self):
        report = _findings_report(("disk-/", "warning", "Disk Space: /"))
        greeting = generate_greeting(report)
        self.assertIn("Disk Space: /", greeting)

    def test_greeting_includes_open_question(self):
        report = _findings_report(("disk-/", "warning", "Disk Space: /"))
        greeting = generate_greeting(report)
        self.assertIn("?", greeting)

    def test_multiple_findings_uses_plural_noun(self):
        report = _findings_report(
            ("disk-/", "warning", "Disk Space: /"),
            ("memory-pressure", "warning", "Memory Pressure"),
        )
        greeting = generate_greeting(report)
        self.assertIn("2 items", greeting)

    def test_more_than_three_findings_shows_overflow(self):
        findings = [
            (f"disk-{i}", "warning", f"Disk {i}") for i in range(5)
        ]
        report = _findings_report(*findings)
        greeting = generate_greeting(report)
        self.assertIn("and 2 more", greeting)


class TestOpenQuestion(unittest.TestCase):
    def test_disk_finding_gives_disk_question(self):
        report = _findings_report(("disk-/", "warning", "Disk Space: /"))
        self.assertIn("disk space", generate_greeting(report).lower())

    def test_memory_finding_gives_memory_question(self):
        report = _findings_report(("memory-pressure", "warning", "Memory Pressure"))
        self.assertIn("memory", generate_greeting(report).lower())

    def test_journal_finding_gives_journal_question(self):
        report = _findings_report(("journal-errors", "warning", "Journal Errors"))
        self.assertIn("log", generate_greeting(report).lower())

    def test_failed_services_gives_services_question(self):
        report = _findings_report(("failed-services", "warning", "Failed Services"))
        self.assertIn("service", generate_greeting(report).lower())


# ---------------------------------------------------------------------------
# launch_diagnostic_greeting — integration tests
# ---------------------------------------------------------------------------

class TestLaunchDiagnosticGreeting(unittest.TestCase):
    def setUp(self):
        self.handle = agent_conversation.start_session()
        self.events: list[tuple[str, dict]] = []
        agent_conversation.on_event(self.handle, lambda t, p: self.events.append((t, p)))

    def tearDown(self):
        agent_conversation.end_session(self.handle)

    def test_healthy_report_emits_healthy_greeting_token(self):
        launch_diagnostic_greeting(self.handle, collect_fn=_healthy_report)
        _wait_for_done(self.events)
        tokens = [p["token"] for t, p in self.events if t == agent_conversation.EVENT_AGENT_TOKEN]
        self.assertTrue(tokens)
        self.assertEqual(tokens[0], GREETING_HEALTHY)

    def test_findings_report_emits_findings_greeting_token(self):
        def _collect():
            return _findings_report(("disk-/", "warning", "Disk Space: /"))

        launch_diagnostic_greeting(self.handle, collect_fn=_collect)
        _wait_for_done(self.events)
        tokens = [p["token"] for t, p in self.events if t == agent_conversation.EVENT_AGENT_TOKEN]
        self.assertTrue(tokens)
        self.assertIn("Disk Space", tokens[0])

    def test_collect_exception_emits_partial_failure_token(self):
        def _bad_collect():
            raise RuntimeError("simulated failure")

        launch_diagnostic_greeting(self.handle, collect_fn=_bad_collect)
        _wait_for_done(self.events)
        tokens = [p["token"] for t, p in self.events if t == agent_conversation.EVENT_AGENT_TOKEN]
        self.assertTrue(tokens)
        self.assertEqual(tokens[0], GREETING_PARTIAL_FAILURE)

    def test_agent_token_event_is_emitted(self):
        launch_diagnostic_greeting(self.handle, collect_fn=_healthy_report)
        _wait_for_done(self.events)
        types = [t for t, _ in self.events]
        self.assertIn(agent_conversation.EVENT_AGENT_TOKEN, types)

    def test_session_done_event_is_emitted(self):
        launch_diagnostic_greeting(self.handle, collect_fn=_healthy_report)
        _wait_for_done(self.events)
        types = [t for t, _ in self.events]
        self.assertIn(agent_conversation.EVENT_SESSION_DONE, types)

    def test_session_done_payload_contains_greeting_key(self):
        launch_diagnostic_greeting(self.handle, collect_fn=_healthy_report)
        _wait_for_done(self.events)
        done_payloads = [p for t, p in self.events if t == agent_conversation.EVENT_SESSION_DONE]
        self.assertTrue(done_payloads)
        self.assertIn("greeting", done_payloads[0])

    def test_greeting_recorded_in_session_history(self):
        launch_diagnostic_greeting(self.handle, collect_fn=_healthy_report)
        _wait_for_done(self.events)
        info = agent_conversation.session_info(self.handle)
        self.assertGreaterEqual(info["history_length"], 1)

    def test_greeting_history_entry_role_is_agent(self):
        launch_diagnostic_greeting(self.handle, collect_fn=_healthy_report)
        _wait_for_done(self.events)
        session = agent_conversation._get_session(self.handle)
        agent_entries = [m for m in session.history() if m["role"] == "agent"]
        self.assertTrue(agent_entries)

    def test_on_loading_callback_called_synchronously(self):
        called: list[str] = []
        launch_diagnostic_greeting(
            self.handle,
            collect_fn=_healthy_report,
            on_loading=lambda msg: called.append(msg),
        )
        # on_loading must have been called before the thread starts
        self.assertEqual(called, [agent_conversation.GREETING_LOADING])


if __name__ == "__main__":
    unittest.main()
