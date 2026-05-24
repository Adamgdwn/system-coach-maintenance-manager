import unittest
from unittest.mock import patch

from system_coach_maintenance_manager.pop_cosmic_brain import analyze_pop_cosmic_issue


class PopCosmicBrainTests(unittest.TestCase):
    def test_fallback_recommends_display_evidence_for_monitor_symptom(self):
        with patch("system_coach_maintenance_manager.pop_cosmic_brain.get_engine_status", return_value={"available": False}):
            analysis = analyze_pop_cosmic_issue(
                "external monitor jumps after suspend",
                {"findings": [{"summary": "COSMIC signal detected."}], "profile": {}},
                [],
                [],
            )

        self.assertEqual(analysis["source"], "deterministic-fallback")
        self.assertEqual(analysis["ranked_actions"][0]["action_key"], "collect-display-state")

    def test_model_action_keys_are_whitelisted(self):
        with patch(
            "system_coach_maintenance_manager.pop_cosmic_brain.get_engine_status",
            return_value={"available": True, "models": ["qwen3:8b"]},
        ), patch(
            "system_coach_maintenance_manager.pop_cosmic_brain._post_json",
            return_value={
                "response": (
                    '{"working_problem":"panel freeze","likely_surface":"panel",'
                    '"hypotheses":[],"ranked_actions":[{"action_key":"rm-rf-home","title":"bad"}],'
                    '"questions":[],"sources_used":[],"confidence":0.5}'
                )
            },
        ):
            analysis = analyze_pop_cosmic_issue("panel freeze", {"findings": [], "profile": {}}, [], [])

        self.assertEqual(analysis["source"], "local-model")
        self.assertEqual(analysis["ranked_actions"][0]["action_key"], "manual")


if __name__ == "__main__":
    unittest.main()
