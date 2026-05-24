import tempfile
import unittest
from pathlib import Path

from system_coach_maintenance_manager.pop_cosmic_knowledge import (
    load_relevant_lessons,
    load_relevant_research,
    save_lesson,
    save_research_records,
)


class PopCosmicKnowledgeTests(unittest.TestCase):
    def test_saves_and_loads_relevant_research_and_lessons(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            profile = {"pop_version": "24.04", "session": {"current_desktop": "COSMIC"}}
            save_research_records(
                [
                    {
                        "title": "COSMIC panel freeze",
                        "summary": "Panel fixes apply to Pop!_OS 24.04.",
                        "applies_to": {"pop_version": "24.04"},
                    }
                ],
                base_dir=base,
            )
            save_lesson(
                {
                    "symptom": "panel freeze after suspend",
                    "profile_hash": "other",
                    "evidence_summary": "cosmic-panel error",
                    "action_taken": "collected logs",
                    "result": "improved",
                    "verification": "logs quieter",
                },
                base_dir=base,
            )

            research = load_relevant_research("panel freeze", profile, base_dir=base)
            lessons = load_relevant_lessons("panel freeze", profile, base_dir=base)

        self.assertEqual(research[0]["title"], "COSMIC panel freeze")
        self.assertEqual(lessons[0]["result"], "improved")


if __name__ == "__main__":
    unittest.main()
