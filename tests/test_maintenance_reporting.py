import unittest

from stack_review_coach.maintenance_reporting import generate_maintenance_report


class MaintenanceReportingTests(unittest.TestCase):
    def _diagnostics(self, os_name, findings):
        return {
            "generated_at": "2026-05-16T12:00:00",
            "metrics": {"platform": {"os": os_name}},
            "command_log": [],
            "findings": findings,
        }

    def _finding(self, finding_id, category, evidence=None):
        return {
            "id": finding_id,
            "title": finding_id.replace("-", " ").title(),
            "category": category,
            "status": "warn",
            "severity": "warning",
            "summary": "Needs review.",
            "evidence": evidence or {},
            "recommended_next_steps": ["Review evidence first."],
            "commands_run": [],
            "requires_privilege": False,
            "can_prepare_action": True,
        }

    def test_generate_maintenance_report_builds_approval_plans(self):
        diagnostics = self._diagnostics(
            "Linux",
            [
                {
                    "id": "disk-_",
                    "title": "Disk Space: /",
                    "category": "disk",
                    "status": "warn",
                    "severity": "warning",
                    "summary": "/ is under disk pressure.",
                    "evidence": {"path": "/", "used_percent": 90},
                    "recommended_next_steps": ["Review large files first."],
                    "commands_run": [],
                    "requires_privilege": False,
                    "can_prepare_action": True,
                },
                {
                    "id": "memory-pressure",
                    "title": "Memory Pressure",
                    "category": "performance",
                    "status": "pass",
                    "severity": "info",
                    "summary": "Memory looks normal.",
                    "evidence": {},
                    "recommended_next_steps": ["Keep monitoring."],
                    "commands_run": [],
                    "requires_privilege": False,
                    "can_prepare_action": False,
                },
            ],
        )

        report = generate_maintenance_report(diagnostics)

        self.assertEqual(report["summary"]["finding_count"], 2)
        self.assertEqual(report["summary"]["approval_required_count"], 1)
        self.assertFalse(report["summary"]["execution_enabled"])
        self.assertEqual(report["action_plans"][0]["finding_id"], "disk-_")
        self.assertTrue(report["action_plans"][0]["approval_required"])
        self.assertIn("du -h", " ".join(report["action_plans"][0]["commands"]))

    def test_windows_log_plan_uses_event_log_commands(self):
        diagnostics = self._diagnostics("Windows", [self._finding("journal-errors", "logs", {"line_count": 3})])

        report = generate_maintenance_report(diagnostics)

        commands = "\n".join(report["action_plans"][0]["commands"])
        self.assertIn("wevtutil", commands)
        self.assertIn("eventvwr.msc", commands)
        self.assertNotIn("journalctl", commands)

    def test_windows_network_plan_uses_windows_route_and_dns_commands(self):
        diagnostics = self._diagnostics(
            "Windows",
            [self._finding("network-basics", "network", {"default_route_detected": False})],
        )

        report = generate_maintenance_report(diagnostics)

        commands = "\n".join(report["action_plans"][0]["commands"])
        self.assertIn("route print", commands)
        self.assertIn("ipconfig /all", commands)
        self.assertNotIn("ip route", commands)

    def test_windows_package_plan_uses_supported_manager_review(self):
        diagnostics = self._diagnostics(
            "Windows",
            [self._finding("package-manager-health", "packages", {"manager": "winget"})],
        )

        report = generate_maintenance_report(diagnostics)

        commands = "\n".join(report["action_plans"][0]["commands"])
        self.assertIn("winget --info", commands)
        self.assertIn("winget source list", commands)
        self.assertNotIn("winget check", commands)

    def test_unknown_platform_returns_triage_plan_without_commands(self):
        diagnostics = self._diagnostics(
            "Haiku",
            [self._finding("network-basics", "network", {"default_route_detected": False})],
        )

        report = generate_maintenance_report(diagnostics)

        plan = report["action_plans"][0]
        self.assertEqual(plan["id"], "plan-network-basics-triage")
        self.assertEqual(plan["commands"], [])
        self.assertIn("unsupported", plan["expected_effect"])


if __name__ == "__main__":
    unittest.main()
