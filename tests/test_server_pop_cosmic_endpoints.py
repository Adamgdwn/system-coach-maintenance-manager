import json
import os
import tempfile
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from subprocess import CompletedProcess
from unittest.mock import patch

from system_coach_maintenance_manager.action_plan_registry import reset_action_plan_registry
from system_coach_maintenance_manager.server import SystemCoachHandler


def _profile() -> dict:
    return {
        "pretty_name": "Pop!_OS 24.04 LTS",
        "pop_version": "24.04",
        "is_pop_os": True,
        "has_cosmic_signal": True,
        "applicable": True,
        "session": {"current_desktop": "COSMIC"},
        "cosmic": {
            "present": ["cosmic-session", "cosmic-settings"],
            "commands": {
                "cosmic-randr": {"present": False, "path": None},
                "cosmic-settings": {"present": True, "path": "/usr/bin/cosmic-settings"},
                "cosmic-store": {"present": True, "path": "/usr/bin/cosmic-store"},
            },
        },
        "support_commands": {},
    }


def _scan(scope: str = "standard") -> dict:
    return {
        "generated_at": "2026-05-24T09:00:00",
        "scope": scope,
        "applicable": True,
        "profile": _profile(),
        "groups": {},
        "findings": [
            {
                "id": "pop-cosmic-missing-support-commands",
                "severity": "warning",
                "summary": "Missing COSMIC support command(s): cosmic-randr.",
            }
        ],
        "privacy": {"redacted_user_paths": True},
    }


class ServerPopCosmicEndpointTests(unittest.TestCase):
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

    def get(self, path: str) -> tuple[int, dict]:
        with urllib.request.urlopen(f"{self.base_url}{path}", timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))

    def post(self, path: str, payload: dict) -> tuple[int, dict]:
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))

    def test_profile_endpoint_returns_detected_environment(self):
        with patch("system_coach_maintenance_manager.server.detect_pop_cosmic_environment", return_value=_profile()):
            status, payload = self.get("/api/pop-cosmic/profile")

        self.assertEqual(status, 200)
        self.assertTrue(payload["applicable"])
        self.assertEqual(payload["pop_version"], "24.04")

    def test_deep_scan_endpoint_returns_requested_scope(self):
        with patch("system_coach_maintenance_manager.server.run_pop_cosmic_deep_scan", return_value=_scan("display")) as scan:
            status, payload = self.post("/api/pop-cosmic/deep-scan", {"scope": "display"})

        self.assertEqual(status, 200)
        self.assertEqual(payload["scope"], "display")
        self.assertEqual(payload["findings"][0]["id"], "pop-cosmic-missing-support-commands")
        scan.assert_called_once_with("display")

    def test_research_endpoint_uses_governed_local_mode(self):
        controls = {
            "source": "test-project-control.yaml",
            "web_research_enabled": False,
            "allowed_domains": ["system76.com"],
            "max_results_per_query": 8,
            "governance_reason": "disabled by test controls",
        }
        with patch("system_coach_maintenance_manager.server.load_pop_cosmic_controls", return_value=controls):
            status, payload = self.post(
                "/api/pop-cosmic/research",
                {"symptom": "COSMIC display issue", "profile": _profile(), "enabled": True},
            )

        self.assertEqual(status, 200)
        self.assertFalse(payload["enabled"])
        self.assertEqual(payload["research_mode"], "official-source-metadata-only")
        self.assertIn("project controls keep it disabled", payload["governance"]["reason"])

    def test_analyze_endpoint_passes_scan_research_and_lessons_to_brain(self):
        analysis = {
            "ok": True,
            "source": "deterministic-fallback",
            "model": None,
            "working_problem": "COSMIC display issue",
            "likely_surface": "display",
            "hypotheses": [],
            "ranked_actions": [{"action_key": "collect-display-state", "title": "Collect display state", "risk": "read_only"}],
            "confidence": 0.35,
        }
        with patch("system_coach_maintenance_manager.server.load_relevant_lessons", return_value=[]), patch(
            "system_coach_maintenance_manager.server.analyze_pop_cosmic_issue", return_value=analysis
        ) as analyze:
            status, payload = self.post(
                "/api/pop-cosmic/analyze",
                {"symptom": "COSMIC display issue", "scan": _scan(), "research": [{"source_id": "manual"}]},
            )

        self.assertEqual(status, 200)
        self.assertEqual(payload["likely_surface"], "display")
        analyze.assert_called_once()
        self.assertEqual(analyze.call_args.args[0], "COSMIC display issue")

    def test_plan_endpoint_registers_blocked_escalation_without_executable_commands(self):
        analysis = {
            "ranked_actions": [
                {
                    "action_key": "apt-repair-step",
                    "title": "Repair package state",
                    "risk": "high",
                }
            ]
        }
        status, payload = self.post("/api/pop-cosmic/plan", {"action_key": "apt-repair-step", "analysis": analysis, "scan": _scan()})

        self.assertEqual(status, 200)
        self.assertTrue(payload["server_plan_id"].startswith("plan-"))
        self.assertFalse(payload["commands"])
        self.assertFalse(payload["action_contract"]["eligible_for_guarded_execution"])
        self.assertTrue(payload["blocked_escalation"]["blocked"])

    def test_execute_endpoint_runs_registered_plan_id(self):
        status, plan = self.post("/api/pop-cosmic/plan", {"action_key": "open-cosmic-settings", "analysis": {}, "scan": _scan()})
        self.assertEqual(status, 200)

        with patch(
            "system_coach_maintenance_manager.maintenance_actions.subprocess.run",
            return_value=CompletedProcess(args=[], returncode=0, stdout="ok\n", stderr=""),
        ) as run:
            status, payload = self.post(
                "/api/pop-cosmic/execute",
                {"plan_id": plan["server_plan_id"], "confirmation_text": plan["action_contract"]["confirmation_phrase"]},
            )

        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["server_plan_id"], plan["server_plan_id"])
        self.assertEqual(run.call_args.args[0], ["cosmic-settings"])

    def test_verify_endpoint_records_unconfirmed_lesson_from_action_result_and_post_scan(self):
        action_result = {"status": "completed", "commands": ["cosmic-settings"]}
        post_scan = _scan("standard")
        post_scan["findings"] = [{"severity": "info", "summary": "COSMIC settings opened; post-scan collected."}]
        with patch("system_coach_maintenance_manager.server.prepare_verification_plan", return_value=post_scan):
            status, payload = self.post(
                "/api/pop-cosmic/verify",
                {
                    "symptom": "COSMIC settings issue",
                    "result": action_result,
                    "scan": _scan(),
                    "user_confirmed": False,
                    "user_note": "Need to observe after reboot.",
                },
            )

        self.assertEqual(status, 200)
        self.assertEqual(payload["lesson"]["result"], "completed_unconfirmed")
        self.assertEqual(payload["lesson"]["action_taken"], "cosmic-settings")
        self.assertIn("COSMIC settings opened", payload["lesson"]["evidence_summary"])
        self.assertEqual(payload["lesson"]["user_note"], "Need to observe after reboot.")


if __name__ == "__main__":
    unittest.main()
