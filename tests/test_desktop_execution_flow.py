import unittest
from unittest.mock import patch


try:
    from system_coach_maintenance_manager.desktop_app import SystemCoachWindow
except (ImportError, ValueError):
    SystemCoachWindow = None


@unittest.skipIf(SystemCoachWindow is None, "GTK desktop shell is not available in this test environment")
class DesktopExecutionFlowTests(unittest.TestCase):
    def test_execution_result_restores_controls_before_result_dialog(self):
        window = SystemCoachWindow.__new__(SystemCoachWindow)
        events = []
        plan = {
            "title": "Collect evidence",
            "family": "display-dock",
            "action_contract": {"id": "action-test"},
        }
        result = {
            "status": "completed",
            "action_id": "action-test",
            "output": "ok",
            "post_check": ["review output"],
        }
        analysis = {"analysis": "Evidence collection completed."}
        window.current_request_plan = plan

        window._prepare_followup_plan_from_execution = lambda *_args: None
        window._plain_plan_summary = lambda *_args: "Plan summary"
        window._set_text = lambda *_args: events.append(("set-text",))
        window._refresh_history_view = lambda: events.append(("refresh-history",))
        window._refresh_approval_queue = lambda: events.append(("refresh-approval",))
        window._set_execution_buttons_sensitive = lambda sensitive: events.append(("buttons", sensitive))
        window._set_status = lambda status: events.append(("status", status))

        def show_dialog(title, _body, entry_text=None):
            events.append(("dialog", title, entry_text))
            self.assertIn(("buttons", True), events)
            self.assertTrue(any(event[0] == "status" for event in events))
            self.assertLess(events.index(("buttons", True)), len(events) - 1)

        window._show_action_dialog = show_dialog

        keep_callback = SystemCoachWindow._apply_execution_result(window, plan, result, analysis)

        self.assertFalse(keep_callback)
        self.assertEqual(events[-1][0], "dialog")

    def test_request_brain_timeout_restores_controls_with_fallback(self):
        class Button:
            def __init__(self):
                self.states = []

            def set_sensitive(self, value):
                self.states.append(value)

        window = SystemCoachWindow.__new__(SystemCoachWindow)
        events = []
        window.REQUEST_BRAIN_TIMEOUT_SECONDS = 1
        window.active_request_brain_token = 7
        window.current_request_plan = None
        window.request_send_button = Button()
        window.prepare_request_button = Button()
        window.execute_request_button = Button()
        window._append_request_message = lambda speaker, text: events.append(("message", speaker, text))
        window._set_status = lambda status: events.append(("status", status))

        keep_timer = SystemCoachWindow._request_brain_timeout(window, 7, "help", False)

        self.assertFalse(keep_timer)
        self.assertIsNone(window.active_request_brain_token)
        self.assertEqual(window.request_send_button.states[-1], True)
        self.assertEqual(window.prepare_request_button.states[-1], True)
        self.assertEqual(window.execute_request_button.states[-1], False)
        self.assertTrue(any("longer than 1 seconds" in event[2] for event in events if event[0] == "message"))

    def test_request_brain_uses_deterministic_fast_path_for_known_requests(self):
        window = SystemCoachWindow.__new__(SystemCoachWindow)
        captured = []

        def idle_add(callback, *args):
            captured.append((callback, args))
            return 1

        with patch("system_coach_maintenance_manager.desktop_app.collect_request_evidence", return_value={"scopes": ["pop-cosmic"]}), patch(
            "system_coach_maintenance_manager.desktop_app.reason_about_request"
        ) as reason_about_request, patch("system_coach_maintenance_manager.desktop_app.GLib.idle_add", side_effect=idle_add):
            SystemCoachWindow._request_brain_worker(
                window,
                3,
                "I lost the ability to select the three icons on the left side of the bottom bar.",
                "Linux",
                "COSMIC",
                None,
                False,
            )

        reason_about_request.assert_not_called()
        self.assertEqual(len(captured), 1)
        _callback, args = captured[0]
        self.assertEqual(args[0], 3)
        self.assertEqual(args[2]["source"], "deterministic-fast-path")
        self.assertEqual(args[2]["family"], "pop-cosmic")

    def test_review_next_backlog_fix_starts_first_executable_maintenance_plan(self):
        class Picker:
            def __init__(self):
                self.active = None

            def set_active(self, index):
                self.active = index

        window = SystemCoachWindow.__new__(SystemCoachWindow)
        events = []
        blocked = {
            "id": "blocked-plan",
            "title": "Blocked plan",
            "execution_enabled": False,
            "action_contract": {"execution_enabled": False},
        }
        executable = {
            "id": "executable-plan",
            "title": "Executable plan",
            "execution_enabled": True,
            "action_contract": {"execution_enabled": True},
        }
        picker = Picker()
        window.current_maintenance = {"action_plans": [blocked, executable]}
        window.queued_plans = [blocked, executable]
        window.approval_plan_picker = picker
        window._refresh_approval_queue = lambda: events.append(("refresh",))
        window._set_status = lambda status: events.append(("status", status))
        window._start_plan_execution = lambda plan: events.append(("start", plan["id"]))

        SystemCoachWindow.on_review_next_backlog_fix(window, None)

        self.assertEqual(picker.active, 1)
        self.assertIn(("start", "executable-plan"), events)

    def test_review_next_backlog_fix_reports_missing_diagnostics(self):
        window = SystemCoachWindow.__new__(SystemCoachWindow)
        events = []
        window.current_maintenance = None
        window._set_status = lambda status: events.append(("status", status))
        window._show_action_dialog = lambda title, body: events.append(("dialog", title, body))

        SystemCoachWindow.on_review_next_backlog_fix(window, None)

        self.assertTrue(any(event[0] == "dialog" and event[1] == "No Maintenance Backlog Yet" for event in events))

    def test_maintenance_findings_dialog_offers_backlog_approval_action(self):
        window = SystemCoachWindow.__new__(SystemCoachWindow)
        events = []
        plan = {
            "id": "plan-journal-errors",
            "title": "Group recent critical log errors",
            "execution_enabled": True,
            "action_contract": {"execution_enabled": True},
        }
        window.current_maintenance = {
            "findings": [{"id": "journal-errors", "summary": "Critical logs found."}],
            "action_plans": [plan],
        }
        window._plain_plan_summary = lambda _plan: "Plain plan summary"
        window.on_review_next_backlog_fix = lambda _button: events.append(("review-next",))

        def show_dialog(title, body, entry_text=None, action_label=None):
            events.append(("dialog", title, action_label, body))
            return "__action__"

        window._show_action_dialog = show_dialog

        with patch("system_coach_maintenance_manager.desktop_app.GLib.idle_add") as idle_add:
            SystemCoachWindow._show_maintenance_findings_dialog(window)

        self.assertTrue(any(event[0] == "dialog" and event[2] == "Review & Approve Next Fix" for event in events))
        self.assertIn(("review-next",), events)
        idle_add.assert_not_called()

    def test_maintenance_plan_summary_explains_journal_troubleshooting_path(self):
        window = SystemCoachWindow.__new__(SystemCoachWindow)
        plan = {
            "id": "plan-journal-errors",
            "finding_id": "journal-errors",
            "title": "Group recent critical log errors",
            "risk": "low",
            "reversible": True,
            "requires_privilege": False,
            "approval_required": True,
            "execution_enabled": True,
            "expected_effect": "Collect log context.",
            "manual_steps": ["Group repeated log lines by service, device, or package."],
            "rollback": [],
            "action_contract": {
                "execution_enabled": True,
                "execution_mode": "user",
                "fingerprint": "abc123",
                "command_preview": ["journalctl -p 3 -n 100 --no-pager"],
                "execution_gate": {"reasons": []},
            },
        }
        window.current_maintenance = {
            "findings": [
                {
                    "id": "journal-errors",
                    "summary": "14 recent critical journal line(s) were found.",
                    "evidence": {
                        "line_count": 14,
                        "sample": [
                            "cosmic-panel: Broken pipe",
                            "cosmic-applet-audio exited with code 137",
                        ],
                    },
                }
            ]
        }

        summary = SystemCoachWindow._plain_plan_summary(window, plan)

        self.assertIn("Critical log lines are evidence, not a fix target", summary)
        self.assertIn("Treat the critical log finding as a symptom", summary)
        self.assertIn("Run a read-only journal query", summary)
        self.assertIn("cosmic-panel: Broken pipe", summary)

    def test_maintenance_plan_summary_includes_local_reasoning_brief(self):
        window = SystemCoachWindow.__new__(SystemCoachWindow)
        plan = {
            "id": "plan-journal-errors",
            "finding_id": "journal-errors",
            "title": "Group recent critical log errors",
            "risk": "low",
            "reversible": True,
            "requires_privilege": False,
            "approval_required": True,
            "execution_enabled": True,
            "expected_effect": "Collect log context.",
            "manual_steps": ["Group repeated log lines by service, device, or package."],
            "rollback": [],
            "maintenance_reasoning": {
                "source": "local-model",
                "model": "qwen3:8b",
                "working_problem": "Critical logs need grouping before repair.",
                "scenario_review": "Could be COSMIC panel state or a secondary service error.",
                "hypotheses": [
                    {
                        "summary": "COSMIC panel is emitting repeated errors.",
                        "supporting_evidence": ["broken pipe sample"],
                        "contradicting_evidence": ["no fresh post-restart logs yet"],
                    }
                ],
                "evidence_assessment": "The log sample supports collecting more context first.",
                "plan_fit": "The journal query is the smallest useful next step.",
                "troubleshooting_path": ["Collect wider log sample", "Group repeated sources"],
                "recommended_next_step": "Run the read-only journal query, then reassess.",
                "approval_guidance": "Approve only the shown journal query.",
                "stop_conditions": ["Do not approve if the command changes services."],
            },
            "action_contract": {
                "execution_enabled": True,
                "execution_mode": "user",
                "fingerprint": "abc123",
                "command_preview": ["journalctl -p 3 -n 100 --no-pager"],
                "execution_gate": {"reasons": []},
            },
        }
        window.current_maintenance = {
            "findings": [
                {
                    "id": "journal-errors",
                    "summary": "14 recent critical journal line(s) were found.",
                    "evidence": {"line_count": 14, "sample": ["cosmic-panel: Broken pipe"]},
                }
            ]
        }

        summary = SystemCoachWindow._plain_plan_summary(window, plan)

        self.assertIn("Reasoning pass:", summary)
        self.assertIn("Source: local-model (qwen3:8b)", summary)
        self.assertIn("Hypotheses considered:", summary)
        self.assertIn("Run the read-only journal query, then reassess.", summary)

    def test_start_plan_execution_runs_maintenance_reasoning_before_approval(self):
        class ImmediateThread:
            def __init__(self, target, args=(), daemon=None):
                self.target = target
                self.args = args

            def start(self):
                self.target(*self.args)

        class Label:
            def set_text(self, text):
                events.append(("gate", text))

        class Notebook:
            def page_num(self, page):
                events.append(("page-num", page))
                return 6

            def set_current_page(self, page_number):
                events.append(("page", page_number))

        window = SystemCoachWindow.__new__(SystemCoachWindow)
        events = []
        approval_page = object()
        approval_selected_view = object()
        plan = {
            "id": "plan-journal-errors",
            "finding_id": "journal-errors",
            "title": "Group recent critical log errors",
            "manual_steps": [],
            "action_contract": {
                "execution_enabled": True,
                "execution_mode": "user",
                "command_preview": ["journalctl -p 3 -n 100 --no-pager"],
            },
        }
        finding = {"id": "journal-errors", "summary": "Critical logs found.", "evidence": {}}
        window.current_maintenance = {"findings": [finding]}
        window.notebook = Notebook()
        window.approval_page = approval_page
        window.approval_selected_view = approval_selected_view
        window.execution_gate_label = Label()
        window._set_text = lambda view, text: events.append(("text", view, text))
        window._set_execution_buttons_sensitive = lambda sensitive: events.append(("buttons", sensitive))
        window._set_status = lambda status: events.append(("status", status))
        window._refresh_selected_plan_preview = lambda: events.append(("preview",))
        window._start_plan_execution = lambda started_plan: events.append(("start", started_plan.get("maintenance_reasoning", {}).get("source")))

        with patch("system_coach_maintenance_manager.desktop_app.threading.Thread", ImmediateThread), patch(
            "system_coach_maintenance_manager.desktop_app.GLib.idle_add", side_effect=lambda callback, *args: callback(*args)
        ), patch(
            "system_coach_maintenance_manager.desktop_app.load_history",
            return_value={"learning_notes": [], "known_good_lessons": [], "changed_since_last": []},
        ), patch(
            "system_coach_maintenance_manager.desktop_app.reason_about_maintenance_plan",
            return_value={"ok": True, "source": "local-model", "model": "qwen3:8b", "recommended_next_step": "Collect evidence."},
        ) as reason:
            SystemCoachWindow._start_plan_execution_with_reasoning(window, plan)

        reason.assert_called_once()
        self.assertEqual(plan["maintenance_reasoning"]["source"], "local-model")
        self.assertIn(("page", 6), events)
        self.assertTrue(
            any(
                event[0] == "text"
                and event[1] is approval_selected_view
                and "Thinking through this maintenance plan before approval" in event[2]
                for event in events
            )
        )
        self.assertIn(("start", "local-model"), events)


if __name__ == "__main__":
    unittest.main()
