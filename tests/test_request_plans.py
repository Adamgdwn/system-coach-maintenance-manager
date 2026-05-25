import unittest

from system_coach_maintenance_manager.request_plans import format_request_plan, prepare_request_plan, review_request_intake


class RequestPlanTests(unittest.TestCase):
    def assert_approval_preview(self, plan):
        self.assertTrue(plan["approval_required"])
        self.assertIn("family", plan)
        self.assertIn("action_contract", plan)
        self.assertEqual(plan["execution_enabled"], plan["action_contract"]["execution_enabled"])

    def test_prepare_linux_cursor_plan_is_approval_required(self):
        plan = prepare_request_plan(
            "My cursor size seems odd. Make it smaller.",
            os_name="Linux",
            distribution_hint="GNOME",
        )

        self.assertEqual(plan["id"], "request-cursor-size-linux")
        self.assert_approval_preview(plan)
        self.assertTrue(plan["execution_enabled"])
        self.assertFalse(plan["requires_privilege"])
        self.assertTrue(any("gsettings set" in command for command in plan["commands"]))
        self.assertIn("GNOME", plan["summary"])

    def test_prepare_kde_cursor_plan_prefers_kde_settings(self):
        plan = prepare_request_plan("Make my pointer bigger", os_name="Linux", distribution_hint="KDE Plasma")

        self.assertEqual(plan["id"], "request-cursor-size-linux")
        self.assertTrue(any("kcmshell" in command for command in plan["commands"]))
        self.assertFalse(any("gsettings set" in command for command in plan["commands"]))
        self.assertTrue(plan["execution_enabled"])

    def test_prepare_cosmic_cursor_plan_uses_cosmic_settings(self):
        plan = prepare_request_plan("Make my cursor larger", os_name="Linux", distribution_hint="COSMIC")

        self.assertEqual(plan["id"], "request-cursor-size-linux")
        self.assertEqual(plan["commands"], ["cosmic-settings"])

    def test_prepare_windows_cursor_plan_opens_settings(self):
        plan = prepare_request_plan("Make my pointer bigger", os_name="Windows")

        self.assertEqual(plan["id"], "request-cursor-size-windows")
        self.assert_approval_preview(plan)
        self.assertTrue(any("ms-settings:easeofaccess-mousepointer" in command for command in plan["commands"]))

    def test_prepare_display_scaling_plan(self):
        plan = prepare_request_plan("Make the display scaling bigger", os_name="Windows")

        self.assertEqual(plan["family"], "display-scaling")
        self.assert_approval_preview(plan)
        self.assertTrue(any("ms-settings:display" in command for command in plan["commands"]))

    def test_prepare_brightness_plan(self):
        plan = prepare_request_plan("Lower the screen brightness", os_name="Linux")

        self.assertEqual(plan["family"], "display-brightness")
        self.assert_approval_preview(plan)
        self.assertIn("brightnessctl info", plan["commands"])

    def test_prepare_night_light_plan(self):
        plan = prepare_request_plan("Turn on night light", os_name="Windows")

        self.assertEqual(plan["family"], "display-night-light")
        self.assert_approval_preview(plan)
        self.assertIn("start ms-settings:nightlight", plan["commands"])

    def test_prepare_refresh_rate_plan(self):
        plan = prepare_request_plan("Check my monitor refresh rate", os_name="Linux")

        self.assertEqual(plan["family"], "display-refresh-rate")
        self.assert_approval_preview(plan)
        self.assertIn("xrandr --query", plan["commands"])

    def test_prepare_display_dock_investigation_does_not_collapse_to_cursor_size(self):
        plan = prepare_request_plan(
            "The screen on my far right is rotated 90 degrees through the Dell docking station, "
            "hides the bottom half, and the cursor movement is jittery.",
            os_name="Linux",
            distribution_hint="COSMIC",
        )

        self.assertEqual(plan["id"], "request-display-dock-linux")
        self.assertEqual(plan["family"], "display-dock")
        self.assert_approval_preview(plan)
        self.assertTrue(plan["execution_enabled"])
        self.assertIn("cosmic-randr list", plan["commands"])
        self.assertIn("lsusb", plan["commands"])
        self.assertIn("journalctl -b -n 500 --no-pager", plan["commands"])
        self.assertIn("not a cursor-size change", plan["summary"])

    def test_prepare_cosmic_display_layout_fix_is_executable(self):
        plan = prepare_request_plan(
            "Apply COSMIC display layout fix. Output DVI-I-1. "
            "Set mode 1920x1080 refresh 60 position 3840,456 scale 1.0 transform normal. "
            "Rollback mode 1920x1080 refresh 60 position 3840,0 scale 1.25 transform rotate90.",
            os_name="Linux",
            distribution_hint="COSMIC",
            family_override="display-layout-fix",
        )

        self.assertEqual(plan["family"], "display-layout-fix")
        self.assertEqual(plan["id"], "request-display-layout-fix-dvi-i-1")
        self.assertTrue(plan["execution_enabled"])
        self.assertFalse(plan["requires_privilege"])
        self.assertEqual(
            plan["commands"][0],
            "cosmic-randr mode DVI-I-1 1920 1080 --refresh 60 --pos-x 3840 --pos-y 456 --scale 1.0 --transform normal",
        )
        self.assertEqual(
            plan["rollback"][0],
            "cosmic-randr mode DVI-I-1 1920 1080 --refresh 60 --pos-x 3840 --pos-y 0 --scale 1.25 --transform rotate90",
        )

    def test_prepare_cosmic_display_layout_fix_from_plain_right_monitor_request(self):
        reasoning = {
            "source": "gemma",
            "model": "gemma4:latest",
            "family": "display-layout-fix",
            "ready": True,
            "confidence": 0.9,
            "reasoning_summary": "Rotate the right monitor and verify behavior.",
            "request_evidence": {
                "scopes": ["display-dock"],
                "commands": [
                    {
                        "command": "cosmic-randr list",
                        "output": """
DVI-I-2 (enabled)
  Model: C27F390
  Position: 1920,0
  Scale: 100%
  Transform: normal
  Modes:
    1920x1080 @ 60.000 Hz (current)
DVI-I-1 (enabled)
  Model: C27F390
  Position: 3840,0
  Scale: 100%
  Transform: normal
  Modes:
    1920x1080 @ 60.000 Hz (current)
""",
                    }
                ],
            },
        }
        plan = prepare_request_plan(
            "The monitor on my right should be rotated 90 degrees. Please rotate it and troubleshoot after.",
            os_name="Linux",
            distribution_hint="COSMIC",
            family_override="display-layout-fix",
            reasoning=reasoning,
        )

        self.assertEqual(plan["family"], "display-layout-fix")
        self.assertTrue(plan["execution_enabled"])
        self.assertIn("--transform rotate90", plan["commands"][0])
        self.assertIn("DVI-I-1", plan["commands"][0])
        self.assertIn("--scale 1.0", plan["commands"][0])

    def test_prepare_plan_accepts_gemma_family_override(self):
        reasoning = {
            "source": "gemma",
            "model": "gemma4:latest",
            "family": "display-dock",
            "ready": True,
            "confidence": 0.88,
            "reasoning_summary": "Gemma identified docked display behavior.",
        }
        plan = prepare_request_plan(
            "The cursor keeps disappearing while dragging windows.",
            os_name="Linux",
            distribution_hint="COSMIC",
            family_override="display-dock",
            reasoning=reasoning,
        )

        self.assertEqual(plan["family"], "display-dock")
        self.assertEqual(plan["reasoning_brain"]["source"], "gemma")
        self.assertEqual(plan["reasoning_brain"]["model"], "gemma4:latest")
        self.assertIn("Reasoning brain: gemma (gemma4:latest)", format_request_plan(plan))

    def test_prepare_audio_plan(self):
        plan = prepare_request_plan("Switch my microphone input", os_name="Linux")

        self.assertEqual(plan["family"], "audio-routing")
        self.assert_approval_preview(plan)
        self.assertTrue(any("pactl list short sources" in command for command in plan["commands"]))

    def test_prepare_pop_cosmic_plan_routes_to_agent_scan(self):
        plan = prepare_request_plan("COSMIC panel freezes after suspend on Pop OS", os_name="Linux", distribution_hint="COSMIC")

        self.assertEqual(plan["id"], "request-pop-cosmic-deep-scan-linux")
        self.assertEqual(plan["family"], "pop-cosmic-deep-scan")
        self.assert_approval_preview(plan)
        self.assertTrue(plan["action_contract"]["eligible_for_guarded_execution"])
        self.assertIn("journalctl --user -b -n 300 --no-pager", plan["commands"])
        self.assertNotIn("apt-get check", plan["commands"])
        self.assertIn("apt-cache policy pop-desktop cosmic-session cosmic-panel cosmic-comp cosmic-settings cosmic-store", plan["commands"])
        self.assertIn("not approval to update", plan["approval_prompt"])

    def test_prepare_cosmic_bottom_bar_request_uses_session_hint(self):
        request = "I lost the ability to select the three icons on the left side of the bottom bar."

        intake = review_request_intake(request, desktop_hint="COSMIC")
        plan = prepare_request_plan(request, os_name="Linux", distribution_hint="COSMIC")

        self.assertTrue(intake["ready"])
        self.assertEqual(intake["family"], "pop-cosmic")
        self.assertIn("bottom-bar interaction", intake["acknowledgement"])
        self.assertEqual(plan["id"], "request-pop-cosmic-deep-scan-linux")
        self.assertEqual(plan["family"], "pop-cosmic-deep-scan")

    def test_prepare_pop_cosmic_panel_restart_plan_is_approved_current_user_action(self):
        plan = prepare_request_plan(
            "Restart the current-user COSMIC panel because bottom-bar icon evidence points to stale panel state.",
            os_name="Linux",
            distribution_hint="COSMIC",
            family_override="pop-cosmic-panel-restart",
            reasoning={
                "source": "deterministic-followup",
                "family": "pop-cosmic-panel-restart",
                "ready": True,
                "reasoning_summary": "Evidence points to stale COSMIC panel state.",
            },
        )

        self.assertEqual(plan["family"], "pop-cosmic-panel-restart")
        self.assertEqual(plan["commands"], ["pkill -TERM -x cosmic-panel"])
        self.assertTrue(plan["execution_enabled"])
        self.assertFalse(plan["requires_privilege"])
        self.assertIn("bottom bar may disappear briefly", " ".join(plan["manual_steps"]))

    def test_prepare_network_dns_plan(self):
        plan = prepare_request_plan("DNS seems broken on my internet", os_name="Windows")

        self.assertEqual(plan["family"], "network-dns")
        self.assert_approval_preview(plan)
        self.assertIn("ipconfig /all", plan["commands"])

    def test_prepare_package_update_plan(self):
        plan = prepare_request_plan("Repair package updates", os_name="Linux")

        self.assertEqual(plan["family"], "package-updates")
        self.assert_approval_preview(plan)
        self.assertTrue(plan["requires_privilege"])
        self.assertIn("apt-get check", plan["commands"])

    def test_prepare_docker_cleanup_plan(self):
        plan = prepare_request_plan("Clean up Docker containers and images", os_name="Linux")

        self.assertEqual(plan["family"], "docker-cleanup")
        self.assert_approval_preview(plan)
        self.assertIn("docker system df", plan["commands"])
        self.assertFalse(any("prune" in command for command in plan["commands"]))

    def test_prepare_startup_apps_plan(self):
        plan = prepare_request_plan("Review startup apps", os_name="Windows")

        self.assertEqual(plan["family"], "startup-apps")
        self.assert_approval_preview(plan)
        self.assertTrue(any("startupapps" in command for command in plan["commands"]))

    def test_prepare_slow_computer_plan(self):
        plan = prepare_request_plan("My computer feels slow and laggy", os_name="Linux")

        self.assertEqual(plan["family"], "slow-computer")
        self.assert_approval_preview(plan)
        self.assertIn("free -h", plan["commands"])

    def test_unknown_request_needs_triage(self):
        plan = prepare_request_plan("Tune the blue sparkle thing", os_name="Linux")
        formatted = format_request_plan(plan)

        self.assertEqual(plan["id"], "request-needs-triage")
        self.assert_approval_preview(plan)
        self.assertIn("No commands prepared yet", formatted)

    def test_request_intake_asks_for_unknown_target(self):
        intake = review_request_intake("the blue sparkle thing is weird")

        self.assertFalse(intake["ready"])
        self.assertEqual(intake["family"], "unknown")
        self.assertTrue(intake["questions"])

    def test_request_intake_accepts_cursor_investigation(self):
        intake = review_request_intake("When I move things around it is jittery and loses the cursor. Can you investigate?")

        self.assertTrue(intake["ready"])
        self.assertEqual(intake["family"], "cursor-size")
        self.assertIn("checking safe pointer settings", intake["acknowledgement"])

    def test_request_intake_routes_display_dock_cursor_symptoms_to_deep_investigation(self):
        intake = review_request_intake(
            "My far right screen through the Dell dock is rotated and the cursor is jittery."
        )

        self.assertTrue(intake["ready"])
        self.assertEqual(intake["family"], "display-dock")
        self.assertIn("display, dock, and compositor", intake["acknowledgement"])

    def test_request_intake_clarifies_vague_cursor_change(self):
        intake = review_request_intake("My cursor seems odd")

        self.assertFalse(intake["ready"])
        self.assertEqual(intake["family"], "cursor-size")
        self.assertTrue(any("smaller" in question for question in intake["questions"]))

    def test_supported_family_on_unknown_platform_triages_without_commands(self):
        plan = prepare_request_plan("Fix my DNS", os_name="Haiku")

        self.assertEqual(plan["id"], "request-network-dns-triage")
        self.assertEqual(plan["commands"], [])
        self.assertIn("unsupported", plan["expected_effect"])


if __name__ == "__main__":
    unittest.main()
