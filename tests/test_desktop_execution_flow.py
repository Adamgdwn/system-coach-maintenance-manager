import unittest


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


if __name__ == "__main__":
    unittest.main()
