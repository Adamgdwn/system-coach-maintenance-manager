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


if __name__ == "__main__":
    unittest.main()
