import unittest

from stack_review_coach.ai_engine import build_context, choose_model


class AiEngineTests(unittest.TestCase):
    def test_choose_model_prefers_known_models(self):
        model = choose_model(["mistral", "gemma4:latest", "qwen3:8b", "other"])
        self.assertEqual(model, "gemma4:latest")

    def test_build_context_includes_report_and_map(self):
        report = {
            "environment": {"os": "Linux", "shell": "/bin/bash"},
            "components": [
                {
                    "label": "Python",
                    "category": "language",
                    "version": "3.12.3",
                    "path": "/usr/bin/python3",
                }
            ],
            "summary": {"primary_stack_matches": [{"title": "Python App Stack", "confidence": "high", "summary": "ready", "coaching": "start with venv"}]},
            "recommendations": ["Use virtual environments."],
        }
        system_map = {
            "summary": {"roots_scanned": 1, "projects_detected": 2},
            "requested_roots": ["/home/tester"],
            "scans": [{"projects": [{"path": "/home/tester/demo", "types": ["Python project"]}]}],
            "config_findings": [{"label": "Git config", "path": "/home/tester/.gitconfig"}],
        }

        maintenance_report = {
            "summary": {"finding_count": 1, "approval_required_count": 1},
            "findings": [
                {
                    "title": "Disk Space: /",
                    "severity": "warning",
                    "summary": "Disk pressure detected.",
                    "recommended_next_steps": ["Prepare a cleanup plan."],
                }
            ],
            "action_plans": [
                {
                    "title": "Investigate disk pressure",
                    "risk": "medium",
                    "requires_privilege": False,
                    "execution_enabled": False,
                }
            ],
        }
        request_plan = {
            "title": "Adjust Linux cursor size",
            "platform": "Linux",
            "risk": "low",
            "requires_privilege": False,
            "execution_enabled": False,
            "approval_prompt": "Approve only after confirming the target size.",
        }

        context = build_context(report, system_map, maintenance_report, request_plan)

        self.assertIn("Python", context)
        self.assertIn("/home/tester/demo", context)
        self.assertIn("Git config", context)
        self.assertIn("Maintenance diagnostics", context)
        self.assertIn("Latest user-requested approval plan", context)


if __name__ == "__main__":
    unittest.main()
