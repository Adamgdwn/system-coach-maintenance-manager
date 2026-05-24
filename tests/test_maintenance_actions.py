import tempfile
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from system_coach_maintenance_manager.maintenance_actions import build_action_contract, execute_guarded_action


class MaintenanceActionsTests(unittest.TestCase):
    def _project_control(self, text: str) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "project-control.yaml"
        path.write_text(text, encoding="utf-8")
        return path

    def test_contract_blocks_execution_when_runner_flag_is_missing(self):
        control_path = self._project_control(
            "\n".join(
                [
                    "governance_level: 1",
                    "agent_controls:",
                    "  autonomy_level: A1",
                ]
            )
        )
        plan = {
            "id": "request-cursor-size-linux",
            "family": "cursor-size",
            "title": "Adjust Linux cursor size",
            "approval_required": True,
            "execution_enabled": False,
            "risk": "low",
            "reversible": True,
            "requires_privilege": False,
            "commands": ["gsettings set org.gnome.desktop.interface cursor-size 24"],
            "expected_effect": "Change the current user's pointer size.",
            "rollback": ["Restore the previous cursor size."],
        }

        contract = build_action_contract(plan, project_control_path=control_path)
        result = execute_guarded_action(contract, contract["confirmation_phrase"])

        self.assertTrue(contract["eligible_for_guarded_execution"])
        self.assertFalse(contract["execution_enabled"])
        self.assertEqual(result["status"], "blocked")
        self.assertIsNone(result["exit_code"])
        self.assertIn("action_runner_enabled", result["error"])

    def test_contract_marks_privileged_or_placeholder_plans_ineligible(self):
        control_path = self._project_control("governance_level: 1\nautonomy_level: A1\naction_runner_enabled: true\n")
        plan = {
            "id": "plan-failed-services",
            "finding_id": "failed-services",
            "title": "Inspect failed services",
            "approval_required": True,
            "execution_enabled": False,
            "risk": "low",
            "reversible": True,
            "requires_privilege": False,
            "commands": ["systemctl status <service-name>"],
            "expected_effect": "Inspect one service.",
            "rollback": [],
        }

        contract = build_action_contract(plan, project_control_path=control_path)

        self.assertFalse(contract["eligible_for_guarded_execution"])
        self.assertFalse(contract["execution_enabled"])
        self.assertTrue(any("placeholder" in reason for reason in contract["eligibility_notes"]))

    def test_enabled_low_risk_contract_executes_guarded_command(self):
        control_path = self._project_control("governance_level: 1\nautonomy_level: A1\naction_runner_enabled: true\n")
        plan = {
            "id": "request-cursor-size-linux",
            "family": "cursor-size",
            "title": "Adjust Linux cursor size",
            "approval_required": True,
            "execution_enabled": False,
            "risk": "low",
            "reversible": True,
            "requires_privilege": False,
            "commands": [
                "gsettings get org.gnome.desktop.interface cursor-size",
                "gsettings set org.gnome.desktop.interface cursor-size 24",
            ],
            "expected_effect": "Change the current user's pointer size.",
            "rollback": ["Restore the previous cursor size."],
        }

        contract = build_action_contract(plan, project_control_path=control_path)

        with patch(
            "system_coach_maintenance_manager.maintenance_actions.subprocess.run",
            return_value=CompletedProcess(args=[], returncode=0, stdout="ok\n", stderr=""),
        ) as run:
            result = execute_guarded_action(contract, contract["confirmation_phrase"])

        self.assertTrue(contract["eligible_for_guarded_execution"])
        self.assertTrue(contract["execution_enabled"])
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(run.call_count, 2)

    def test_enabled_contract_blocks_empty_confirmation(self):
        control_path = self._project_control("governance_level: 1\nautonomy_level: A1\naction_runner_enabled: true\n")
        plan = {
            "id": "request-cursor-size-linux",
            "family": "cursor-size",
            "title": "Adjust Linux cursor size",
            "approval_required": True,
            "execution_enabled": False,
            "risk": "low",
            "reversible": True,
            "requires_privilege": False,
            "commands": ["gsettings set org.gnome.desktop.interface cursor-size 24"],
            "expected_effect": "Change the current user's pointer size.",
            "rollback": ["Restore the previous cursor size."],
        }

        contract = build_action_contract(plan, project_control_path=control_path)

        with patch("system_coach_maintenance_manager.maintenance_actions.subprocess.run") as run:
            result = execute_guarded_action(contract, "")

        self.assertTrue(contract["execution_enabled"])
        self.assertEqual(result["status"], "blocked")
        self.assertIn("confirmation phrase", result["error"])
        run.assert_not_called()

    def test_enabled_contract_blocks_wrong_confirmation(self):
        control_path = self._project_control("governance_level: 1\nautonomy_level: A1\naction_runner_enabled: true\n")
        plan = {
            "id": "request-cursor-size-linux",
            "family": "cursor-size",
            "title": "Adjust Linux cursor size",
            "approval_required": True,
            "execution_enabled": False,
            "risk": "low",
            "reversible": True,
            "requires_privilege": False,
            "commands": ["gsettings set org.gnome.desktop.interface cursor-size 24"],
            "expected_effect": "Change the current user's pointer size.",
            "rollback": ["Restore the previous cursor size."],
        }

        contract = build_action_contract(plan, project_control_path=control_path)

        with patch("system_coach_maintenance_manager.maintenance_actions.subprocess.run") as run:
            result = execute_guarded_action(contract, "APPROVE something-else")

        self.assertEqual(result["status"], "blocked")
        self.assertIn("confirmation phrase", result["error"])
        run.assert_not_called()

    def test_enabled_contract_blocks_missing_confirmation_phrase(self):
        control_path = self._project_control("governance_level: 1\nautonomy_level: A1\naction_runner_enabled: true\n")
        plan = {
            "id": "request-cursor-size-linux",
            "family": "cursor-size",
            "title": "Adjust Linux cursor size",
            "approval_required": True,
            "execution_enabled": False,
            "risk": "low",
            "reversible": True,
            "requires_privilege": False,
            "commands": ["gsettings set org.gnome.desktop.interface cursor-size 24"],
            "expected_effect": "Change the current user's pointer size.",
            "rollback": ["Restore the previous cursor size."],
        }

        contract = build_action_contract(plan, project_control_path=control_path)
        del contract["confirmation_phrase"]

        with patch("system_coach_maintenance_manager.maintenance_actions.subprocess.run") as run:
            result = execute_guarded_action(contract, "")

        self.assertEqual(result["status"], "blocked")
        self.assertIn("confirmation phrase", result["error"])
        run.assert_not_called()

    def test_read_only_evidence_plan_executes_guarded_commands(self):
        control_path = self._project_control("governance_level: 1\nautonomy_level: A1\naction_runner_enabled: true\n")
        plan = {
            "id": "plan-journal-errors",
            "finding_id": "journal-errors",
            "title": "Group recent critical log errors",
            "approval_required": True,
            "execution_enabled": False,
            "risk": "low",
            "reversible": True,
            "requires_privilege": False,
            "commands": ["journalctl -p 3 -n 100 --no-pager"],
            "expected_effect": "Collect recent critical log lines.",
            "rollback": [],
        }

        contract = build_action_contract(plan, project_control_path=control_path)

        with patch(
            "system_coach_maintenance_manager.maintenance_actions.subprocess.run",
            return_value=CompletedProcess(args=[], returncode=0, stdout="log lines\n", stderr=""),
        ) as run:
            result = execute_guarded_action(contract, contract["confirmation_phrase"])

        self.assertTrue(contract["eligible_for_guarded_execution"])
        self.assertTrue(contract["execution_enabled"])
        self.assertEqual(result["status"], "completed")
        self.assertEqual(run.call_count, 1)

    def test_display_dock_evidence_plan_executes_guarded_read_only_commands(self):
        control_path = self._project_control("governance_level: 1\nautonomy_level: A1\naction_runner_enabled: true\n")
        plan = {
            "id": "request-display-dock-linux",
            "family": "display-dock",
            "title": "Investigate Linux display, dock, and pointer behavior",
            "approval_required": True,
            "execution_enabled": False,
            "risk": "low",
            "reversible": True,
            "requires_privilege": False,
            "commands": ["cosmic-randr list", "xrandr --query", "lsusb", "lspci", "journalctl -b -n 500 --no-pager"],
            "expected_effect": "Collect read-only display and dock evidence.",
            "rollback": [],
        }

        contract = build_action_contract(plan, project_control_path=control_path)

        with patch(
            "system_coach_maintenance_manager.maintenance_actions.subprocess.run",
            return_value=CompletedProcess(args=[], returncode=0, stdout="evidence\n", stderr=""),
        ) as run:
            result = execute_guarded_action(contract, contract["confirmation_phrase"])

        self.assertTrue(contract["eligible_for_guarded_execution"])
        self.assertTrue(contract["execution_enabled"])
        self.assertEqual(result["status"], "completed")
        self.assertEqual(run.call_count, 5)

    def test_display_layout_fix_executes_guarded_cosmic_command(self):
        control_path = self._project_control("governance_level: 1\nautonomy_level: A1\naction_runner_enabled: true\n")
        plan = {
            "id": "request-display-layout-fix-dvi-i-1",
            "family": "display-layout-fix",
            "title": "Apply COSMIC display layout fix to DVI-I-1",
            "approval_required": True,
            "execution_enabled": False,
            "risk": "low",
            "reversible": True,
            "requires_privilege": False,
            "commands": [
                "cosmic-randr mode DVI-I-1 1920 1080 --refresh 60 --pos-x 3840 --pos-y 456 --scale 1.0 --transform normal",
                "cosmic-randr list",
            ],
            "expected_effect": "Change a user-session display layout.",
            "rollback": [
                "cosmic-randr mode DVI-I-1 1920 1080 --refresh 60 --pos-x 3840 --pos-y 0 --scale 1.25 --transform rotate90"
            ],
        }

        contract = build_action_contract(plan, project_control_path=control_path)

        with patch(
            "system_coach_maintenance_manager.maintenance_actions.subprocess.run",
            return_value=CompletedProcess(args=[], returncode=0, stdout="ok\n", stderr=""),
        ) as run:
            result = execute_guarded_action(contract, contract["confirmation_phrase"])

        self.assertTrue(contract["eligible_for_guarded_execution"])
        self.assertTrue(contract["execution_enabled"])
        self.assertEqual(result["status"], "completed")
        self.assertEqual(run.call_count, 2)

    def test_elevated_plan_requires_elevated_runner_flag(self):
        control_path = self._project_control("governance_level: 1\nautonomy_level: A1\naction_runner_enabled: true\n")
        plan = {
            "id": "plan-package-manager-health",
            "family": "package-manager-health",
            "title": "Review apt package health",
            "approval_required": True,
            "execution_enabled": False,
            "risk": "medium",
            "reversible": False,
            "requires_privilege": True,
            "commands": ["apt-get check"],
            "expected_effect": "Review package manager health with administrator privileges.",
            "rollback": [],
        }

        contract = build_action_contract(plan, project_control_path=control_path)

        self.assertTrue(contract["eligible_for_guarded_execution"])
        self.assertFalse(contract["execution_enabled"])
        self.assertEqual(contract["execution_mode"], "elevated")
        self.assertTrue(any("elevated_action_runner_enabled" in reason for reason in contract["execution_gate"]["reasons"]))

    def test_elevated_plan_executes_through_pkexec(self):
        control_path = self._project_control(
            "governance_level: 1\nautonomy_level: A1\naction_runner_enabled: true\nelevated_action_runner_enabled: true\n"
        )
        plan = {
            "id": "plan-package-manager-health",
            "family": "package-manager-health",
            "title": "Review apt package health",
            "approval_required": True,
            "execution_enabled": False,
            "risk": "medium",
            "reversible": False,
            "requires_privilege": True,
            "commands": ["apt-get check"],
            "expected_effect": "Review package manager health with administrator privileges.",
            "rollback": [],
        }

        contract = build_action_contract(plan, project_control_path=control_path)

        with patch("system_coach_maintenance_manager.maintenance_actions.shutil.which", return_value="/usr/bin/pkexec"), patch(
            "system_coach_maintenance_manager.maintenance_actions.subprocess.run",
            return_value=CompletedProcess(args=[], returncode=0, stdout="ok\n", stderr=""),
        ) as run:
            result = execute_guarded_action(contract, contract["confirmation_phrase"])

        self.assertTrue(contract["eligible_for_guarded_execution"])
        self.assertTrue(contract["execution_enabled"])
        self.assertEqual(contract["execution_mode"], "elevated")
        self.assertEqual(contract["elevation_prompt"]["method"], "pkexec")
        self.assertEqual(result["status"], "completed")
        self.assertEqual(run.call_args.args[0][:2], ["pkexec", "apt-get"])


if __name__ == "__main__":
    unittest.main()
