import unittest

from system_coach_maintenance_manager.pop_cosmic_research import research_pop_cosmic_issue, safe_research_query


class PopCosmicResearchTests(unittest.TestCase):
    def test_research_disabled_returns_official_records_without_fetching(self):
        profile = {"pop_version": "24.04"}
        result = research_pop_cosmic_issue("COSMIC panel freezes after suspend", profile, enabled=False)

        self.assertFalse(result["enabled"])
        self.assertIn("Pop!_OS 24.04 COSMIC", result["query"])
        self.assertTrue(result["records"])
        self.assertTrue(all(record["trust_level"] == "official" for record in result["records"]))

    def test_safe_query_does_not_include_raw_home_paths(self):
        query = safe_research_query("panel failed in /home/alice/private", {"pop_version": "24.04"})

        self.assertNotIn("/home/alice", query)


if __name__ == "__main__":
    unittest.main()
