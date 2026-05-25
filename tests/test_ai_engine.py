import unittest
import urllib.error
from unittest.mock import patch

from system_coach_maintenance_manager.ai_engine import (
    analyze_action_result,
    build_context,
    build_maintenance_reasoning_prompt,
    build_request_reasoning_prompt,
    choose_model,
    choose_request_brain_model,
    reason_about_maintenance_plan,
    reason_about_request,
)


class AiEngineTests(unittest.TestCase):
    def test_choose_model_prefers_known_models(self):
        model = choose_model(["mistral", "gemma4:latest", "qwen3:8b", "other"])
        self.assertEqual(model, "qwen3:8b")

    def test_choose_model_uses_gemma_when_qwen_is_missing(self):
        model = choose_model(["qwen3:8b", "gemma4:26b", "mistral"])
        self.assertEqual(model, "qwen3:8b")

        model = choose_model(["gemma4:26b", "mistral"])
        self.assertEqual(model, "gemma4:26b")

    def test_choose_model_accepts_new_local_model_family_fallbacks(self):
        self.assertEqual(choose_model(["qwen3:8b", "deepseek-r1:14b"]), "qwen3:8b")
        self.assertEqual(choose_model(["qwen3-vl:8b", "gpt-oss:20b"]), "gpt-oss:20b")

    def test_choose_request_brain_uses_local_ladder(self):
        self.assertEqual(choose_request_brain_model(["qwen3:8b", "gemma4"]), "qwen3:8b")
        self.assertEqual(choose_request_brain_model(["gemma4", "deepseek-r1:14b"]), "gemma4")
        self.assertEqual(choose_request_brain_model(["deepseek-r1:14b", "gpt-oss:20b"]), "deepseek-r1:14b")

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

    def test_request_prompt_contains_universal_troubleshooting_method(self):
        prompt = build_request_reasoning_prompt(
            "The monitor on the right is behaving oddly.",
            os_name="Linux",
            desktop_hint="COSMIC",
            request_evidence={"scopes": ["display-dock"], "commands": []},
            learning_context=["A prior display lane needed a layout fix."],
        )

        self.assertIn("System access model", prompt)
        self.assertIn("Troubleshooting method", prompt)
        self.assertIn("Build multiple hypotheses", prompt)
        self.assertIn("permission_plan", prompt)
        self.assertIn("The family is the current investigation lane, not a final diagnosis", prompt)

    def test_build_maintenance_reasoning_prompt_uses_troubleshooting_method(self):
        prompt = build_maintenance_reasoning_prompt(
            {
                "title": "Group recent critical log errors",
                "commands": ["journalctl -p 3 -n 100 --no-pager"],
                "risk": "low",
            },
            {
                "id": "journal-errors",
                "summary": "14 critical log lines found.",
                "evidence": {"sample": ["cosmic-panel broken pipe"]},
            },
            learning_context=["A prior panel restart fixed stale COSMIC state."],
        )

        self.assertIn("before an approval dialog", prompt)
        self.assertIn("Build multiple hypotheses", prompt)
        self.assertIn("Do not invent shell commands", prompt)
        self.assertIn("journalctl -p 3 -n 100 --no-pager", prompt)

    def test_reason_about_maintenance_plan_uses_local_model_structured_json(self):
        with patch(
            "system_coach_maintenance_manager.ai_engine._get_json",
            return_value={"models": [{"name": "qwen3:8b"}]},
        ), patch(
            "system_coach_maintenance_manager.ai_engine._post_json",
            return_value={
                "response": (
                    '{"working_problem":"Critical logs need grouping before repair.",'
                    '"scenario_review":"The log finding may be COSMIC panel related or a secondary error.",'
                    '"hypotheses":[{"summary":"COSMIC panel is producing repeated errors",'
                    '"supporting_evidence":["broken pipe sample"],"contradicting_evidence":["no fresh panel logs"]}],'
                    '"evidence_assessment":"Current evidence supports log grouping first.",'
                    '"plan_fit":"The journal query is the smallest useful next step.",'
                    '"troubleshooting_path":["Collect wider log sample","Group repeated sources"],'
                    '"recommended_next_step":"Run the read-only journal query, then reassess.",'
                    '"approval_guidance":"Approve only the shown journal query.",'
                    '"stop_conditions":["Do not approve if the command changes services."],'
                    '"confidence":0.82}'
                )
            },
        ):
            result = reason_about_maintenance_plan(
                {"title": "Group recent critical log errors", "commands": ["journalctl -p 3 -n 100 --no-pager"]},
                {"id": "journal-errors", "summary": "14 critical log lines found.", "evidence": {"sample": ["broken pipe"]}},
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["source"], "local-model")
        self.assertEqual(result["model"], "qwen3:8b")
        self.assertIn("COSMIC panel", result["scenario_review"])
        self.assertEqual(result["troubleshooting_path"][0], "Collect wider log sample")
        self.assertIn("journal query", result["recommended_next_step"])

    def test_reason_about_maintenance_plan_falls_back_without_model(self):
        with patch(
            "system_coach_maintenance_manager.ai_engine._get_json",
            side_effect=urllib.error.URLError("offline"),
        ):
            result = reason_about_maintenance_plan(
                {"title": "Group recent critical log errors", "expected_effect": "Collect log context."},
                {"id": "journal-errors", "summary": "14 critical log lines found.", "evidence": {"sample": ["broken pipe"]}},
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["source"], "deterministic-maintenance-brief")
        self.assertIn("larger recent error sample", " ".join(result["troubleshooting_path"]))

    def test_reason_about_request_uses_local_model_structured_json(self):
        with patch(
            "system_coach_maintenance_manager.ai_engine._get_json",
            return_value={"models": [{"name": "qwen3:8b"}, {"name": "gemma4:latest"}]},
        ), patch(
            "system_coach_maintenance_manager.ai_engine._post_json",
            return_value={
                "response": (
                    '{"family":"display-dock","ready":true,'
                    '"acknowledgement":"This looks like a docked display issue.",'
                    '"questions":[],"alternate_families":["display"],'
                    '"evidence_assessment":"Monitor evidence supports a display lane; logs could disprove dock involvement.",'
                    '"investigation_steps":["Read monitor topology","Compare right monitor with siblings"],'
                    '"permission_plan":"Read-only evidence can run now; display changes need Execute approval.",'
                    '"reasoning_summary":"External rotated monitor via dock.",'
                    '"confidence":0.91}'
                )
            },
        ):
            result = reason_about_request(
                "My far right screen through the Dell dock is rotated and the cursor is jittery.",
                os_name="Linux",
                desktop_hint="COSMIC",
                learning_context=["Previous rotated monitor evidence produced a layout fix."],
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["source"], "local-model")
        self.assertEqual(result["model"], "qwen3:8b")
        self.assertEqual(result["family"], "display-dock")
        self.assertEqual(result["alternate_families"], ["display"])
        self.assertIn("supports", result["evidence_assessment"])
        self.assertEqual(result["investigation_steps"][0], "Read monitor topology")
        self.assertIn("Execute approval", result["permission_plan"])
        self.assertTrue(result["ready"])

    def test_reason_about_request_rejects_unknown_model_family(self):
        with patch(
            "system_coach_maintenance_manager.ai_engine._get_json",
            return_value={"models": [{"name": "gemma4:latest"}]},
        ), patch(
            "system_coach_maintenance_manager.ai_engine._post_json",
            return_value={
                "response": (
                    '{"family":"run-random-shell","ready":true,'
                    '"acknowledgement":"I classified it.",'
                    '"questions":[],"reasoning_summary":"Bad family."}'
                )
            },
        ):
            result = reason_about_request("do a thing", os_name="Linux")

        self.assertTrue(result["ok"])
        self.assertEqual(result["family"], "unknown")

    def test_reason_about_request_uses_evidence_scope_when_model_is_empty(self):
        with patch(
            "system_coach_maintenance_manager.ai_engine._get_json",
            return_value={"models": [{"name": "gemma4:latest"}]},
        ), patch(
            "system_coach_maintenance_manager.ai_engine._post_json",
            return_value={"response": '{"family":"unknown","ready":false,"acknowledgement":"","questions":[]}'},
        ):
            result = reason_about_request(
                "Something is wrong.",
                os_name="Linux",
                request_evidence={"scopes": ["network-dns"], "commands": [{"command": "ip route", "output": "default via 1.1.1.1"}]},
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["family"], "network-dns")
        self.assertTrue(result["ready"])
        self.assertIn("network-dns", result["acknowledgement"])

    def test_reason_about_request_preserves_display_dock_scope_when_model_says_display(self):
        with patch(
            "system_coach_maintenance_manager.ai_engine._get_json",
            return_value={"models": [{"name": "gemma4:latest"}]},
        ), patch(
            "system_coach_maintenance_manager.ai_engine._post_json",
            return_value={
                "response": (
                    '{"family":"display","ready":true,'
                    '"acknowledgement":"This is a display problem.",'
                    '"questions":[],"reasoning_summary":"Evidence shows docked display behavior."}'
                )
            },
        ):
            result = reason_about_request(
                "Monitor through dock is rotated and jittery.",
                os_name="Linux",
                request_evidence={"scopes": ["display-dock"], "commands": [{"command": "xrandr --query", "output": "DVI-I-1 rotate90"}]},
            )

        self.assertEqual(result["family"], "display-dock")

    def test_reason_about_request_falls_back_to_heavier_model_on_invalid_json(self):
        with patch(
            "system_coach_maintenance_manager.ai_engine._get_json",
            return_value={"models": [{"name": "qwen3:8b"}, {"name": "gemma4:latest"}]},
        ), patch(
            "system_coach_maintenance_manager.ai_engine._post_json",
            side_effect=[
                {"response": "not json"},
                {"response": '{"family":"display","ready":true,"acknowledgement":"I classified it.","questions":[]}'},
            ],
        ) as post_json:
            result = reason_about_request("fix my display", os_name="Linux")

        self.assertTrue(result["ok"])
        self.assertEqual(result["source"], "local-model")
        self.assertEqual(result["model"], "gemma4:latest")
        self.assertEqual(post_json.call_count, 2)

    def test_analyze_action_result_uses_local_ladder(self):
        with patch(
            "system_coach_maintenance_manager.ai_engine._get_json",
            return_value={"models": [{"name": "qwen3:8b"}, {"name": "gemma4:latest"}]},
        ), patch(
            "system_coach_maintenance_manager.ai_engine._post_json",
            return_value={"response": "What I found\nDisplayLink dock evidence.\n\nBest next fix\nPrepare a display layout reset."},
        ):
            result = analyze_action_result(
                {"title": "Investigate display dock", "family": "display-dock"},
                {"status": "completed", "output": "Dell Universal Dock D6000\nSamsung C27F390"},
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["model"], "qwen3:8b")
        self.assertIn("DisplayLink", result["analysis"])


if __name__ == "__main__":
    unittest.main()
