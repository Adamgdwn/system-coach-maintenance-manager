import tempfile
import unittest
from pathlib import Path

from system_coach_maintenance_manager.pop_cosmic_controls import load_pop_cosmic_controls
from system_coach_maintenance_manager.pop_cosmic_research import research_pop_cosmic_issue, safe_research_query


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
                        "  max_results_per_query: 3",
                        "  cache_ttl_days: 2",
                        "  mode: guided-fix",
                    ]
                ),
                encoding="utf-8",
            )
            controls = load_pop_cosmic_controls(path)

        self.assertTrue(controls["web_research_enabled"])
        self.assertEqual(controls["allowed_domains"], ["system76.com", "github.com/pop-os"])
        self.assertEqual(controls["max_results_per_query"], 3)
        self.assertEqual(controls["cache_ttl_days"], 2)


if __name__ == "__main__":
    unittest.main()
