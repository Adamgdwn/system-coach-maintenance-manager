import tempfile
import unittest
from pathlib import Path

from system_coach_maintenance_manager.maintenance_history import (
    apply_recent_fix_overrides,
    format_history,
    load_history,
    record_action_result,
    record_approval_decision,
    record_learning_note,
    record_maintenance_report,
    record_request_plan,
)


class MaintenanceHistoryTests(unittest.TestCase):
    def test_records_reports_plans_and_decisions_locally(self):
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            report = {
                "generated_at": "2026-05-16T12:00:00",
                "summary": {
                    "finding_count": 2,
                    "severity_counts": {"info": 2},
                    "approval_required_count": 0,
                    "execution_enabled": False,
                },
                "findings": [],
                "action_plans": [],
            }
            plan = {
                "title": "Plan network troubleshooting",
                "family": "network-dns",
                "platform": "Linux",
                "risk": "low",
                "approval_required": True,
                "execution_enabled": False,
                "requires_privilege": False,
            }

            record_maintenance_report(report, base_dir=base_dir)
            record_request_plan(plan, base_dir=base_dir)
            record_approval_decision({"decision": "deferred", "plan_id": "plan-1"}, base_dir=base_dir)
            record_learning_note(
                {
                    "family": "display-dock",
                    "status": "completed",
                    "lesson": "Rotated external display evidence led to a display layout fix.",
                    "followup_family": "display-layout-fix",
                },
                base_dir=base_dir,
            )

            history = load_history(base_dir=base_dir)
            formatted = format_history(history)

        self.assertEqual(history["summary"]["record_count"], 4)
        self.assertEqual(history["summary"]["kind_counts"]["maintenance_report"], 1)
        self.assertEqual(history["summary"]["kind_counts"]["request_plan"], 1)
        self.assertEqual(history["summary"]["kind_counts"]["learning_note"], 1)
        self.assertIn("no critical or warning findings", history["known_good_lessons"][0])
        self.assertIn("Rotated external display", history["learning_notes"][0])
        self.assertIn("Not enough maintenance history", history["changed_since_last"][0])
        self.assertIn("network-dns", formatted)
        self.assertIn("Learning notes", formatted)

    def test_history_summarizes_changes_between_diagnostics(self):
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            first = {
                "summary": {
                    "finding_count": 1,
                    "severity_counts": {"info": 1},
                    "approval_required_count": 0,
                    "execution_enabled": False,
                },
                "findings": [
                    {"id": "memory-pressure", "title": "Memory Pressure", "severity": "info", "status": "pass", "summary": "ok"}
                ],
            }
            second = {
                "summary": {
                    "finding_count": 2,
                    "severity_counts": {"info": 1, "warning": 1},
                    "approval_required_count": 1,
                    "execution_enabled": False,
                },
                "findings": [
                    {"id": "memory-pressure", "title": "Memory Pressure", "severity": "info", "status": "pass", "summary": "ok"},
                    {"id": "network-basics", "title": "Network Basics", "severity": "warning", "status": "warn", "summary": "dns issue"},
                ],
            }

            record_maintenance_report(first, base_dir=base_dir)
            record_maintenance_report(second, base_dir=base_dir)
            history = load_history(base_dir=base_dir)

        self.assertTrue(any("Network Basics" in change for change in history["changed_since_last"]))

    def test_recent_panel_restart_moves_journal_finding_to_monitor_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            record_action_result(
                {
                    "action_id": "action-request-pop-cosmic-panel-restart-linux",
                    "plan_id": "request-pop-cosmic-panel-restart-linux",
                    "status": "completed",
                    "exit_code": 0,
                    "execution_enabled": True,
                    "commands": ["pkill -TERM -x cosmic-panel"],
                },
                base_dir=base_dir,
            )
            report = {
                "summary": {
                    "finding_count": 1,
                    "status_counts": {"warn": 1},
                    "severity_counts": {"warning": 1},
                    "approval_required_count": 1,
                    "execution_enabled": True,
                },
                "findings": [
                    {
                        "id": "journal-errors",
                        "title": "Recent Critical Logs",
                        "status": "warn",
                        "severity": "warning",
                        "summary": "14 recent critical journal line(s) were found.",
                        "evidence": {"sample": ["cosmic-panel: Broken pipe"]},
                        "recommended_next_steps": ["Group repeated log lines."],
                        "can_prepare_action": True,
                    }
                ],
                "action_plans": [
                    {
                        "id": "plan-journal-errors",
                        "finding_id": "journal-errors",
                        "title": "Group recent critical log errors",
                        "execution_enabled": True,
                    }
                ],
                "recommendations": ["Start with critical findings."],
            }

            updated = apply_recent_fix_overrides(report, base_dir=base_dir)

        finding = updated["findings"][0]
        self.assertEqual(finding["status"], "monitor")
        self.assertEqual(finding["severity"], "info")
        self.assertFalse(finding["can_prepare_action"])
        self.assertEqual(updated["action_plans"], [])
        self.assertEqual(updated["summary"]["approval_required_count"], 0)
        self.assertFalse(updated["summary"]["execution_enabled"])
        self.assertIn("history_resolution", finding["evidence"])
        self.assertIn("monitor mode", updated["recommendations"][0])

    def test_recent_panel_restart_does_not_hide_unrelated_journal_finding(self):
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            record_action_result(
                {
                    "action_id": "action-request-pop-cosmic-panel-restart-linux",
                    "plan_id": "request-pop-cosmic-panel-restart-linux",
                    "status": "completed",
                    "exit_code": 0,
                    "execution_enabled": True,
                    "commands": ["pkill -TERM -x cosmic-panel"],
                },
                base_dir=base_dir,
            )
            report = {
                "summary": {
                    "finding_count": 1,
                    "status_counts": {"warn": 1},
                    "severity_counts": {"warning": 1},
                    "approval_required_count": 1,
                    "execution_enabled": True,
                },
                "findings": [
                    {
                        "id": "journal-errors",
                        "title": "Recent Critical Logs",
                        "status": "warn",
                        "severity": "warning",
                        "summary": "Kernel reported unrelated storage errors.",
                        "evidence": {"sample": ["kernel: nvme timeout"]},
                        "recommended_next_steps": ["Group repeated log lines."],
                        "can_prepare_action": True,
                    }
                ],
                "action_plans": [{"id": "plan-journal-errors", "finding_id": "journal-errors"}],
                "recommendations": [],
            }

            updated = apply_recent_fix_overrides(report, base_dir=base_dir)

        self.assertEqual(updated["findings"][0]["status"], "warn")
        self.assertEqual(updated["findings"][0]["severity"], "warning")
        self.assertEqual(updated["action_plans"][0]["finding_id"], "journal-errors")


if __name__ == "__main__":
    unittest.main()
