import tempfile
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from system_coach_maintenance_manager.maintenance_actions import execute_guarded_action
from system_coach_maintenance_manager.pop_cosmic_actions import (
    make_verification_lesson,
    prepare_pop_cosmic_action,
    verification_result_label,
)


class PopCosmicActionsTests(unittest.TestCase):
    def _project_control(self) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "project-control.yaml"
        path.write_text("governance_level: 1\nautonomy_level: A1\naction_runner_enabled: true\n", encoding="utf-8")
        return path

    def test_collect_update_state_builds_read_only_executable_plan(self):
        plan = prepare_pop_cosmic_action("collect-update-state", {"ranked_actions": []}, {})

        self.assertEqual(plan["family"], "pop-cosmic-update-check")
        self.assertTrue(plan["action_contract"]["eligible_for_guarded_execution"])
        self.assertFalse(any("full-upgrade" in command or " install " in command for command in plan["commands"]))

    def test_blocked_high_risk_action_has_no_commands(self):
        plan = prepare_pop_cosmic_action("apt-repair-step", {"ranked_actions": []}, {})

        self.assertFalse(plan["commands"])
        self.assertFalse(plan["action_contract"]["eligible_for_guarded_execution"])
        self.assertTrue(plan["blocked_escalation"]["blocked"])
        self.assertTrue(plan["blocked_escalation"]["requires_new_contract"])
        self.assertGreaterEqual(len(plan["blocked_escalation"]["next_steps"]), 2)

    def test_pop_cosmic_plan_still_requires_confirmation(self):
        plan = prepare_pop_cosmic_action("open-cosmic-settings", {"ranked_actions": []}, {})

        contract = plan["action_contract"]
        contract["execution_enabled"] = True
        with patch(
            "system_coach_maintenance_manager.maintenance_actions.subprocess.run",
            return_value=CompletedProcess(args=[], returncode=0, stdout="ok\n", stderr=""),
        ) as run:
            blocked = execute_guarded_action(contract, "")
            completed = execute_guarded_action(contract, contract["confirmation_phrase"])

        self.assertEqual(blocked["status"], "blocked")
        self.assertEqual(completed["status"], "completed")
        self.assertEqual(run.call_count, 1)

    def test_verification_labels_require_user_confirmation_for_improvement(self):
        self.assertEqual(
            verification_result_label({"status": "completed"}, user_confirmed=False),
            "completed_unconfirmed",
        )
        self.assertEqual(
            verification_result_label({"status": "completed"}, user_confirmed=True),
            "user_confirmed_improved",
        )
        self.assertEqual(verification_result_label({"status": "failed"}, user_confirmed=True), "not_completed")

    def test_verification_lesson_records_result_evidence_and_user_state(self):
        lesson = make_verification_lesson(
            symptom="panel freeze",
            action_result={"status": "completed", "commands": ["cosmic-settings"]},
            post_scan={
                "profile": {"pop_version": "24.04", "session": {"current_desktop": "COSMIC"}},
                "findings": [{"summary": "COSMIC signal still present."}],
            },
            user_confirmed=False,
            user_note="Panel still needs observation.",
        )

        self.assertEqual(lesson["result"], "completed_unconfirmed")
        self.assertIn("COSMIC signal still present", lesson["evidence_summary"])
        self.assertEqual(lesson["action_taken"], "cosmic-settings")
        self.assertIn("User has not confirmed improvement", lesson["verification"])
        self.assertEqual(lesson["user_note"], "Panel still needs observation.")


if __name__ == "__main__":
    unittest.main()
