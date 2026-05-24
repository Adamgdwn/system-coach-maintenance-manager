import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from system_coach_maintenance_manager.pop_cosmic_controls import load_pop_cosmic_controls
from system_coach_maintenance_manager.pop_cosmic_research import (
    GitHubCosmicProvider,
    OfficialSystem76Provider,
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

    def read(self):
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


if __name__ == "__main__":
    unittest.main()
