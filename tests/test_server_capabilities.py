import json
import os
import tempfile
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from unittest.mock import patch

from system_coach_maintenance_manager.server import SystemCoachHandler


class ServerCapabilityTests(unittest.TestCase):
    def setUp(self):
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
        if self.previous_history_dir is None:
            os.environ.pop("SYSTEM_COACH_HISTORY_DIR", None)
        else:
            os.environ["SYSTEM_COACH_HISTORY_DIR"] = self.previous_history_dir
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


if __name__ == "__main__":
    unittest.main()
