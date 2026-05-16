import unittest

from stack_review_coach.request_plans import format_request_plan, prepare_request_plan


class RequestPlanTests(unittest.TestCase):
    def test_prepare_linux_cursor_plan_is_approval_required(self):
        plan = prepare_request_plan(
            "My cursor size seems odd. Make it smaller.",
            os_name="Linux",
            distribution_hint="GNOME",
        )

        self.assertEqual(plan["id"], "request-cursor-size-linux")
        self.assertTrue(plan["approval_required"])
        self.assertFalse(plan["execution_enabled"])
        self.assertFalse(plan["requires_privilege"])
        self.assertTrue(any("gsettings set" in command for command in plan["commands"]))
        self.assertIn("GNOME", plan["summary"])

    def test_prepare_kde_cursor_plan_prefers_kde_settings(self):
        plan = prepare_request_plan("Make my pointer bigger", os_name="Linux", distribution_hint="KDE Plasma")

        self.assertEqual(plan["id"], "request-cursor-size-linux")
        self.assertTrue(any("kcmshell" in command for command in plan["commands"]))
        self.assertFalse(any("gsettings set" in command for command in plan["commands"]))

    def test_prepare_cosmic_cursor_plan_uses_cosmic_settings(self):
        plan = prepare_request_plan("Make my cursor larger", os_name="Linux", distribution_hint="COSMIC")

        self.assertEqual(plan["id"], "request-cursor-size-linux")
        self.assertEqual(plan["commands"], ["cosmic-settings"])

    def test_prepare_windows_cursor_plan_opens_settings(self):
        plan = prepare_request_plan("Make my pointer bigger", os_name="Windows")

        self.assertEqual(plan["id"], "request-cursor-size-windows")
        self.assertTrue(plan["approval_required"])
        self.assertFalse(plan["execution_enabled"])
        self.assertTrue(any("ms-settings:easeofaccess-mousepointer" in command for command in plan["commands"]))

    def test_unknown_request_needs_triage(self):
        plan = prepare_request_plan("Tune the blue sparkle thing", os_name="Linux")
        formatted = format_request_plan(plan)

        self.assertEqual(plan["id"], "request-needs-triage")
        self.assertIn("No commands prepared yet", formatted)


if __name__ == "__main__":
    unittest.main()
