import json
import os
import tempfile
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from unittest.mock import patch

from system_coach_maintenance_manager.server import SystemCoachHandler


class ServerPopCosmicResearchTests(unittest.TestCase):
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

    def post(self, path: str, payload: dict) -> tuple[int, dict]:
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))

    def test_payload_cannot_enable_disabled_web_research(self):
        controls = {
            "source": "test-project-control.yaml",
            "web_research_enabled": False,
            "allowed_domains": ["system76.com", "github.com/pop-os"],
            "max_results_per_query": 8,
            "governance_reason": "disabled by test controls",
        }
        with patch("system_coach_maintenance_manager.server.load_pop_cosmic_controls", return_value=controls), patch(
            "system_coach_maintenance_manager.pop_cosmic_research.GitHubCosmicProvider.search"
        ) as github_search:
            status, payload = self.post(
                "/api/pop-cosmic/research",
                {
                    "symptom": "COSMIC panel freeze",
                    "profile": {"pop_version": "24.04"},
                    "enabled": True,
                    "include_github": True,
                },
            )

        self.assertEqual(status, 200)
        self.assertFalse(payload["enabled"])
        self.assertFalse(payload["live_web_enabled"])
        self.assertFalse(payload["governance"]["effective_live_web"])
        self.assertEqual(payload["research_mode"], "official-source-metadata-only")
        self.assertIn("project controls keep it disabled", payload["governance"]["reason"])
        github_search.assert_not_called()

    def test_enabled_project_controls_allow_live_github_search_when_requested(self):
        controls = {
            "source": "test-project-control.yaml",
            "web_research_enabled": True,
            "allowed_domains": ["system76.com", "github.com/pop-os", "api.github.com"],
            "max_results_per_query": 8,
            "governance_reason": "enabled by test controls",
        }
        github_records = [
            {
                "source_id": "github-123",
                "provider": "github",
                "title": "COSMIC panel issue",
                "url": "https://github.com/pop-os/cosmic-epoch/issues/123",
                "published_or_updated": "2026-05-01T00:00:00Z",
                "retrieved_at": "2026-05-24T09:00:00",
                "trust_level": "maintainer",
                "summary": "COSMIC panel issue",
                "relevant_evidence": ["open"],
                "risk_notes": [],
                "applies_to": {"pop_version": "unknown", "cosmic_version": "Epoch 1|unknown", "hardware": "unknown"},
                "record_mode": "live-web-search",
            }
        ]
        with patch("system_coach_maintenance_manager.server.load_pop_cosmic_controls", return_value=controls), patch(
            "system_coach_maintenance_manager.pop_cosmic_research.GitHubCosmicProvider.search",
            return_value=github_records,
        ) as github_search:
            status, payload = self.post(
                "/api/pop-cosmic/research",
                {
                    "symptom": "COSMIC panel freeze",
                    "profile": {"pop_version": "24.04"},
                    "enabled": True,
                    "include_github": True,
                },
            )

        self.assertEqual(status, 200)
        self.assertTrue(payload["enabled"])
        self.assertTrue(payload["governance"]["effective_live_web"])
        self.assertEqual(payload["research_mode"], "live-web-search")
        self.assertTrue(any(record["record_mode"] == "live-web-search" for record in payload["records"]))
        github_search.assert_called_once()


if __name__ == "__main__":
    unittest.main()
