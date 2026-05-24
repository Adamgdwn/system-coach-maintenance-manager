import tempfile
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from system_coach_maintenance_manager.maintenance_actions import execute_guarded_action
from system_coach_maintenance_manager.pop_cosmic_actions import prepare_pop_cosmic_action


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


if __name__ == "__main__":
    unittest.main()
