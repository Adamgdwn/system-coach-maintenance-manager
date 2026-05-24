import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from subprocess import CompletedProcess
from unittest.mock import patch

from system_coach_maintenance_manager.action_plan_registry import reset_action_plan_registry
from system_coach_maintenance_manager.maintenance_actions import attach_action_contract
from system_coach_maintenance_manager.server import SystemCoachHandler


def _safe_plan() -> dict:
    return attach_action_contract(
        {
            "id": "server-registry-display-query",
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
    )


class ServerActionPlanRegistryTests(unittest.TestCase):
    def setUp(self):
        reset_action_plan_registry()
        self.history_dir = tempfile.TemporaryDirectory()
        self.previous_history_dir = os.environ.get("SYSTEM_COACH_HISTORY_DIR")
        os.environ["SYSTEM_COACH_HISTORY_DIR"] = self.history_dir.name
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), SystemCoachHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        reset_action_plan_registry()
        if self.previous_history_dir is None:
            os.environ.pop("SYSTEM_COACH_HISTORY_DIR", None)
        else:
            os.environ["SYSTEM_COACH_HISTORY_DIR"] = self.previous_history_dir
        self.history_dir.cleanup()

    def post(self, path: str, payload: dict, *, expect_error: bool = False) -> tuple[int, dict]:
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if not expect_error:
                raise
            return exc.code, json.loads(exc.read().decode("utf-8"))

    def test_direct_contract_submission_is_rejected(self):
        contract = _safe_plan()["action_contract"]

        with patch("system_coach_maintenance_manager.maintenance_actions.subprocess.run") as run:
            status, payload = self.post(
                "/api/action-run",
                {"contract": contract, "confirmation_text": contract["confirmation_phrase"]},
                expect_error=True,
            )

        self.assertEqual(status, 400)
        self.assertEqual(payload["status"], "blocked")
        self.assertIn("plan_id", payload["error"])
        run.assert_not_called()

    def test_valid_plan_id_execution_works(self):
        status, plan = self.post("/api/pop-cosmic/plan", {"action_key": "collect-display-state"})
        self.assertEqual(status, 200)
        contract = plan["action_contract"]

        with patch(
            "system_coach_maintenance_manager.maintenance_actions.subprocess.run",
            return_value=CompletedProcess(args=[], returncode=0, stdout="ok\n", stderr=""),
        ) as run:
            status, result = self.post(
                "/api/action-run",
                {"plan_id": plan["server_plan_id"], "confirmation_text": contract["confirmation_phrase"]},
            )

        self.assertEqual(status, 200)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["server_plan_id"], plan["server_plan_id"])
        self.assertEqual(run.call_args_list[0].args[0], ["cosmic-randr", "list"])

    def test_modified_client_contract_is_ignored_when_plan_id_is_valid(self):
        status, plan = self.post("/api/pop-cosmic/plan", {"action_key": "collect-display-state"})
        self.assertEqual(status, 200)
        contract = dict(plan["action_contract"])
        contract["command_preview"] = ["cosmic-store"]

        with patch(
            "system_coach_maintenance_manager.maintenance_actions.subprocess.run",
            return_value=CompletedProcess(args=[], returncode=0, stdout="ok\n", stderr=""),
        ) as run:
            status, result = self.post(
                "/api/action-run",
                {
                    "plan_id": plan["server_plan_id"],
                    "confirmation_text": plan["action_contract"]["confirmation_phrase"],
                    "contract": contract,
                },
            )

        self.assertEqual(status, 200)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(run.call_args_list[0].args[0], ["cosmic-randr", "list"])

    def test_used_plan_cannot_execute_twice_through_api(self):
        status, plan = self.post("/api/pop-cosmic/plan", {"action_key": "open-cosmic-settings"})
        self.assertEqual(status, 200)
        confirmation = plan["action_contract"]["confirmation_phrase"]

        with patch(
            "system_coach_maintenance_manager.maintenance_actions.subprocess.run",
            return_value=CompletedProcess(args=[], returncode=0, stdout="ok\n", stderr=""),
        ) as run:
            first_status, first = self.post(
                "/api/action-run",
                {"plan_id": plan["server_plan_id"], "confirmation_text": confirmation},
            )
            second_status, second = self.post(
                "/api/action-run",
                {"plan_id": plan["server_plan_id"], "confirmation_text": confirmation},
            )

        self.assertEqual(first_status, 200)
        self.assertEqual(first["status"], "completed")
        self.assertEqual(second_status, 200)
        self.assertEqual(second["status"], "blocked")
        self.assertIn("already used", second["error"])
        self.assertEqual(run.call_count, 1)

    def test_confirmation_phrase_mismatch_fails_through_api(self):
        status, plan = self.post("/api/pop-cosmic/plan", {"action_key": "open-cosmic-settings"})
        self.assertEqual(status, 200)

        with patch("system_coach_maintenance_manager.maintenance_actions.subprocess.run") as run:
            status, result = self.post(
                "/api/action-run",
                {"plan_id": plan["server_plan_id"], "confirmation_text": "APPROVE wrong"},
            )

        self.assertEqual(status, 200)
        self.assertEqual(result["status"], "blocked")
        self.assertIn("confirmation phrase", result["error"])
        run.assert_not_called()

    def test_pop_cosmic_execute_uses_registry_path(self):
        status, plan = self.post("/api/pop-cosmic/plan", {"action_key": "open-cosmic-settings"})
        self.assertEqual(status, 200)

        with patch(
            "system_coach_maintenance_manager.maintenance_actions.subprocess.run",
            return_value=CompletedProcess(args=[], returncode=0, stdout="ok\n", stderr=""),
        ) as run:
            status, result = self.post(
                "/api/pop-cosmic/execute",
                {
                    "plan_id": plan["server_plan_id"],
                    "confirmation_text": plan["action_contract"]["confirmation_phrase"],
                },
            )

        self.assertEqual(status, 200)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["server_plan_id"], plan["server_plan_id"])
        self.assertEqual(run.call_args.args[0], ["cosmic-settings"])


if __name__ == "__main__":
    unittest.main()
