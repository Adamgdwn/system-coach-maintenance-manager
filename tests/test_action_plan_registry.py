import unittest
from subprocess import CompletedProcess
from unittest.mock import patch

from system_coach_maintenance_manager.action_plan_registry import ActionPlanRegistry
from system_coach_maintenance_manager.maintenance_actions import attach_action_contract


def _safe_plan() -> dict:
    plan = {
        "id": "registry-test-display-query",
        "family": "display-refresh-rate",
        "title": "Collect display mode",
        "approval_required": True,
        "risk": "low",
        "reversible": True,
        "requires_privilege": False,
        "commands": ["xrandr --query"],
        "expected_effect": "Collect display mode evidence.",
        "rollback": ["No machine change is made."],
    }
    return attach_action_contract(plan)


class ActionPlanRegistryTests(unittest.TestCase):
    def test_expired_plan_cannot_execute(self):
        registry = ActionPlanRegistry(ttl_seconds=-1)
        plan = registry.register_plan(_safe_plan())

        result = registry.execute(plan["server_plan_id"], plan["action_contract"]["confirmation_phrase"])

        self.assertEqual(result["status"], "blocked")
        self.assertIn("expired", result["error"])

    def test_used_plan_cannot_execute_twice(self):
        registry = ActionPlanRegistry()
        plan = registry.register_plan(_safe_plan())

        with patch(
            "system_coach_maintenance_manager.maintenance_actions.subprocess.run",
            return_value=CompletedProcess(args=[], returncode=0, stdout="ok\n", stderr=""),
        ) as run:
            first = registry.execute(plan["server_plan_id"], plan["action_contract"]["confirmation_phrase"])
            second = registry.execute(plan["server_plan_id"], plan["action_contract"]["confirmation_phrase"])

        self.assertEqual(first["status"], "completed")
        self.assertEqual(second["status"], "blocked")
        self.assertIn("already used", second["error"])
        self.assertEqual(run.call_count, 1)

    def test_confirmation_mismatch_fails_without_running_command(self):
        registry = ActionPlanRegistry()
        plan = registry.register_plan(_safe_plan())

        with patch("system_coach_maintenance_manager.maintenance_actions.subprocess.run") as run:
            result = registry.execute(plan["server_plan_id"], "APPROVE the-wrong-action")

        self.assertEqual(result["status"], "blocked")
        self.assertIn("confirmation phrase", result["error"])
        run.assert_not_called()

    def test_fingerprint_mismatch_blocks_execution(self):
        registry = ActionPlanRegistry()
        plan = registry.register_plan(_safe_plan())
        stored = registry._plans[plan["server_plan_id"]]
        stored.contract["command_preview"] = ["cosmic-store"]

        with patch("system_coach_maintenance_manager.maintenance_actions.subprocess.run") as run:
            result = registry.execute(plan["server_plan_id"], plan["action_contract"]["confirmation_phrase"])

        self.assertEqual(result["status"], "blocked")
        self.assertIn("fingerprint", result["error"])
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
