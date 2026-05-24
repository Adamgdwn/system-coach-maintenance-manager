import json
import os
import tempfile
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from system_coach_maintenance_manager.server import SystemCoachHandler


class ServerCapabilityTests(unittest.TestCase):
    def setUp(self):
        self.history_dir = tempfile.TemporaryDirectory()
        self.previous_history_dir = os.environ.get("SYSTEM_COACH_HISTORY_DIR")
        self.previous_provider_config = os.environ.get("SYSTEM_COACH_MODEL_PROVIDER_CONFIG")
        os.environ["SYSTEM_COACH_HISTORY_DIR"] = self.history_dir.name
        os.environ["SYSTEM_COACH_MODEL_PROVIDER_CONFIG"] = str(Path(self.history_dir.name) / "providers.json")
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), SystemCoachHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        if self.previous_history_dir is None:
            os.environ.pop("SYSTEM_COACH_HISTORY_DIR", None)
        else:
            os.environ["SYSTEM_COACH_HISTORY_DIR"] = self.previous_history_dir
        if self.previous_provider_config is None:
            os.environ.pop("SYSTEM_COACH_MODEL_PROVIDER_CONFIG", None)
        else:
            os.environ["SYSTEM_COACH_MODEL_PROVIDER_CONFIG"] = self.previous_provider_config
        self.history_dir.cleanup()

    def test_capabilities_endpoint_returns_machine_profile(self):
        profile = {
            "generated_at": "2026-05-24T10:00:00",
            "onboarding_mode": "unknown-machine-first-run",
            "surfaces": [{"id": "request-desk", "available": True}],
            "local_storage": {"repository_storage_allowed": False},
        }
        with patch("system_coach_maintenance_manager.server.detect_system_capabilities", return_value=profile):
            with urllib.request.urlopen(f"{self.base_url}/api/capabilities", timeout=5) as response:
                payload = json.loads(response.read().decode("utf-8"))

        self.assertEqual(response.status, 200)
        self.assertEqual(payload["onboarding_mode"], "unknown-machine-first-run")
        self.assertFalse(payload["local_storage"]["repository_storage_allowed"])

    def test_model_provider_endpoint_saves_redacted_settings(self):
        request = urllib.request.Request(
            f"{self.base_url}/api/model-provider",
            data=json.dumps(
                {
                    "active_mode": "cloud",
                    "cloud": {
                        "enabled": True,
                        "provider": "openai-compatible",
                        "base_url": "https://api.openai.com/v1",
                        "model": "example-model",
                        "api_key_env_var": "SYSTEM_COACH_TEST_KEY",
                        "api_key": "sk-never-return",
                    },
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with patch.dict(os.environ, {"SYSTEM_COACH_TEST_KEY": "sk-env-secret"}, clear=False):
            with urllib.request.urlopen(request, timeout=5) as response:
                payload = json.loads(response.read().decode("utf-8"))

        raw_response = json.dumps(payload)
        saved_text = Path(os.environ["SYSTEM_COACH_MODEL_PROVIDER_CONFIG"]).read_text(encoding="utf-8")
        self.assertEqual(response.status, 200)
        self.assertEqual(payload["active_mode"], "cloud")
        self.assertEqual(payload["effective_mode"], "cloud")
        self.assertTrue(payload["config"]["cloud"]["api_key_present"])
        self.assertIn("Raw API key fields were ignored", payload["save_warnings"][0])
        self.assertNotIn("sk-never-return", raw_response)
        self.assertNotIn("sk-env-secret", raw_response)
        self.assertNotIn("sk-never-return", saved_text)


if __name__ == "__main__":
    unittest.main()
