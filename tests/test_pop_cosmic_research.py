import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from system_coach_maintenance_manager.pop_cosmic_controls import load_pop_cosmic_controls
from system_coach_maintenance_manager.pop_cosmic_research import (
    GitHubCosmicProvider,
    OfficialSystem76Provider,
    PerplexityResearchProvider,
    research_pop_cosmic_issue,
    research_url_allowed,
    safe_research_query,
)


class _FakeResponse:
    def __init__(self, text: str):
        self.text = text

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, _size=None):
        return self.text.encode("utf-8")


class PopCosmicResearchTests(unittest.TestCase):
    def test_research_disabled_returns_official_records_without_fetching(self):
        profile = {"pop_version": "24.04"}
        result = research_pop_cosmic_issue("COSMIC panel freezes after suspend", profile, enabled=False)

        self.assertFalse(result["enabled"])
        self.assertEqual(result["research_mode"], "official-source-metadata-only")
        self.assertIn("Pop!_OS 24.04 COSMIC", result["query"])
        self.assertTrue(result["records"])
        self.assertTrue(all(record["trust_level"] == "official" for record in result["records"]))
        self.assertTrue(all(record["record_mode"] == "official-source-metadata" for record in result["records"]))

    def test_safe_query_does_not_include_raw_home_paths(self):
        query = safe_research_query("panel failed in /home/alice/private", {"pop_version": "24.04"})

        self.assertNotIn("/home/alice", query)

    def test_pop_cosmic_controls_default_to_disabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            controls = load_pop_cosmic_controls(Path(tmp) / "missing-project-control.yaml")

        self.assertFalse(controls["web_research_enabled"])
        self.assertIn("disabled", controls["governance_reason"])

    def test_pop_cosmic_controls_parse_research_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "project-control.yaml"
            path.write_text(
                "\n".join(
                    [
                        "project_name: test",
                        "pop_cosmic_agent:",
                        "  web_research_enabled: true",
                        "  allowed_domains:",
                        "    - system76.com",
                        "    - github.com/pop-os",
                        "    - api.github.com/repos/pop-os",
                        "  research_provider: perplexity",
                        "  perplexity_api_key_env_var: PERPLEXITY_API_KEY",
                        "  perplexity_model_env_var: PERPLEXITY_MODEL",
                        "  master_env_path: /tmp/master.env",
                        "  max_results_per_query: 3",
                        "  cache_ttl_days: 2",
                        "  mode: guided-fix",
                    ]
                ),
                encoding="utf-8",
            )
            controls = load_pop_cosmic_controls(path)

        self.assertTrue(controls["web_research_enabled"])
        self.assertEqual(controls["allowed_domains"], ["system76.com", "github.com/pop-os", "api.github.com/repos/pop-os"])
        self.assertEqual(controls["research_provider"], "perplexity")
        self.assertEqual(controls["perplexity_api_key_env_var"], "PERPLEXITY_API_KEY")
        self.assertEqual(controls["perplexity_model_env_var"], "PERPLEXITY_MODEL")
        self.assertEqual(controls["master_env_path"], "/tmp/master.env")
        self.assertEqual(controls["max_results_per_query"], 3)
        self.assertEqual(controls["cache_ttl_days"], 2)

    def test_allows_official_system76_https_urls(self):
        self.assertTrue(research_url_allowed("https://support.system76.com/articles/package-manager-pop/"))
        self.assertTrue(research_url_allowed("https://blog.system76.com/post/cosmic-epoch-1-updates/"))
        self.assertTrue(research_url_allowed("https://system76.com/pop/download/"))

    def test_allows_official_pop_os_github_urls(self):
        self.assertTrue(research_url_allowed("https://github.com/pop-os/cosmic-epoch/issues/123"))
        self.assertTrue(research_url_allowed("https://github.com/pop-os/pop-upgrade"))
        self.assertTrue(research_url_allowed("https://api.github.com/repos/pop-os/cosmic-epoch/issues/123"))

    def test_rejects_non_https_unknown_and_broad_github_urls(self):
        self.assertFalse(research_url_allowed("http://support.system76.com/articles/package-manager-pop/"))
        self.assertFalse(research_url_allowed("https://example.com/pop-os/cosmic"))
        self.assertFalse(research_url_allowed("https://github.com/other-org/cosmic-epoch/issues/123"))
        self.assertFalse(research_url_allowed("https://github.com/pop-os/unrelated-repo/issues/123"))

    def test_fetch_rejects_unrelated_github_url(self):
        provider = GitHubCosmicProvider(enabled=True)

        with self.assertRaises(ValueError):
            provider.fetch("https://github.com/other-org/cosmic-epoch/issues/123")

    def test_fetch_rejects_unrelated_system76_domain(self):
        provider = OfficialSystem76Provider(enabled=True)

        with self.assertRaises(ValueError):
            provider.fetch("https://support.system76.evil.example/articles/package-manager-pop/")

    def test_github_search_filters_unrelated_result_urls(self):
        provider = GitHubCosmicProvider(enabled=True)
        payload = (
            '{"items": ['
            '{"number": 1, "title": "Good", "html_url": "https://github.com/pop-os/cosmic-epoch/issues/1", "state": "open"},'
            '{"number": 2, "title": "Bad", "html_url": "https://github.com/other-org/cosmic-epoch/issues/2", "state": "open"}'
            "]}"
        )

        with patch(
            "system_coach_maintenance_manager.pop_cosmic_research.urllib.request.urlopen",
            return_value=_FakeResponse(payload),
        ):
            records = provider.search("Pop!_OS COSMIC panel", max_results=8)

        self.assertEqual([record["title"] for record in records], ["Good"])

    def test_perplexity_search_uses_master_env_and_filters_allowed_urls(self):
        provider = PerplexityResearchProvider(
            enabled=True,
            allowed_domains=("support.system76.com", "github.com/pop-os"),
            master_env_path="/tmp/master.env",
        )
        payload = json.dumps(
            {
                "choices": [{"message": {"content": "Panel applets may need COSMIC panel investigation."}}],
                "search_results": [
                    {
                        "title": "Allowed support result",
                        "url": "https://support.system76.com/articles/package-manager-pop/",
                        "snippet": "Official support article.",
                    },
                    {
                        "title": "Rejected result",
                        "url": "https://example.com/cosmic-panel",
                        "snippet": "Untrusted.",
                    },
                ],
                "citations": ["https://github.com/pop-os/cosmic-panel/issues/1", "https://example.com/nope"],
            }
        )

        with patch("system_coach_maintenance_manager.pop_cosmic_research._read_env_file_value") as read_env, patch(
            "system_coach_maintenance_manager.pop_cosmic_research.urllib.request.urlopen",
            return_value=_FakeResponse(payload),
        ) as urlopen:
            read_env.side_effect = lambda _path, key: "pplx-test" if key == "PERPLEXITY_API_KEY" else "sonar-pro"
            records = provider.search("Pop!_OS COSMIC bottom bar icons", max_results=8)

        self.assertTrue(any(record["provider"] == "perplexity" for record in records))
        self.assertTrue(any(record["url"] == "https://support.system76.com/articles/package-manager-pop/" for record in records))
        self.assertTrue(any(record["url"] == "https://github.com/pop-os/cosmic-panel/issues/1" for record in records))
        self.assertFalse(any(record["url"] == "https://example.com/cosmic-panel" for record in records))
        request = urlopen.call_args.args[0]
        self.assertEqual(request.headers["Authorization"], "Bearer pplx-test")

    def test_perplexity_research_mode_records_live_provider(self):
        profile = {"pop_version": "24.04"}
        records = [
            {
                "source_id": "perplexity-1",
                "provider": "perplexity",
                "title": "COSMIC panel research",
                "url": "https://support.system76.com/articles/package-manager-pop/",
                "published_or_updated": "unknown",
                "retrieved_at": "2026-05-24T09:00:00",
                "trust_level": "allowed-web",
                "summary": "Research summary",
                "relevant_evidence": [],
                "risk_notes": [],
                "applies_to": {"pop_version": "unknown", "cosmic_version": "unknown", "hardware": "unknown"},
                "record_mode": "live-web-search",
            }
        ]

        with patch(
            "system_coach_maintenance_manager.pop_cosmic_research.PerplexityResearchProvider.search",
            return_value=records,
        ) as perplexity_search:
            result = research_pop_cosmic_issue(
                "COSMIC panel icons cannot be selected",
                profile,
                enabled=True,
                research_provider="perplexity",
                allowed_domains=["support.system76.com"],
                perplexity_config={"master_env_path": "/tmp/master.env"},
            )

        self.assertEqual(result["research_mode"], "live-web-perplexity-search")
        self.assertTrue(any(record["provider"] == "perplexity" for record in result["records"]))
        perplexity_search.assert_called_once()


if __name__ == "__main__":
    unittest.main()
