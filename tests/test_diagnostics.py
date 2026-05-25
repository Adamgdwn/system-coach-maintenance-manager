import unittest
from collections import namedtuple
from unittest.mock import patch

from system_coach_maintenance_manager.diagnostics import collect_diagnostics


class DiagnosticsTests(unittest.TestCase):
    def test_collect_diagnostics_returns_read_only_findings(self):
        usage = namedtuple("usage", ["total", "used", "free"])
        disk_usage = usage(total=1000, used=900, free=100)
        meminfo = {
            "MemTotal": 1000,
            "MemAvailable": 80,
            "SwapTotal": 200,
            "SwapFree": 100,
        }

        def fake_command(args, timeout=6):
            command = " ".join(args)
            if args[:2] == ["systemctl", "--failed"]:
                return {"command": command, "exit_code": 0, "output": "demo.service failed", "duration_ms": 1}
            if args[:2] == ["journalctl", "-p"]:
                return {"command": command, "exit_code": 0, "output": "kernel: demo critical line", "duration_ms": 1}
            if args[:3] == ["ip", "route", "show"]:
                return {"command": command, "exit_code": 0, "output": "default via 192.0.2.1", "duration_ms": 1}
            if args[:2] == ["apt-get", "check"]:
                return {"command": command, "exit_code": 0, "output": "ok", "duration_ms": 1}
            if args[:2] == ["findmnt", "--json"]:
                return {
                    "command": command,
                    "exit_code": 0,
                    "output": '{"filesystems":[{"source":"/dev/root","target":"/","fstype":"ext4","options":"rw"}]}',
                    "duration_ms": 1,
                }
            return {"command": command, "exit_code": 0, "output": "", "duration_ms": 1}

        with patch("system_coach_maintenance_manager.diagnostics.shutil.disk_usage", return_value=disk_usage), patch(
            "system_coach_maintenance_manager.diagnostics._read_meminfo", return_value=meminfo
        ), patch("system_coach_maintenance_manager.diagnostics._run_command", side_effect=fake_command), patch(
            "system_coach_maintenance_manager.diagnostics.shutil.which", return_value="/usr/bin/tool"
        ), patch(
            "system_coach_maintenance_manager.diagnostics.socket.getaddrinfo", return_value=[("ok",)]
        ):
            report = collect_diagnostics()

        self.assertIn("findings", report)
        self.assertIn("desktop", report["metrics"])
        self.assertTrue(any(finding["id"] == "memory-pressure" for finding in report["findings"]))
        self.assertTrue(any(finding["id"] == "failed-services" for finding in report["findings"]))
        self.assertTrue(report["command_log"])

    def test_non_root_apt_lock_denial_uses_dpkg_audit_without_warning(self):
        usage = namedtuple("usage", ["total", "used", "free"])
        disk_usage = usage(total=1000, used=100, free=900)
        meminfo = {
            "MemTotal": 1000,
            "MemAvailable": 900,
            "SwapTotal": 200,
            "SwapFree": 200,
        }

        def fake_command(args, timeout=6):
            command = " ".join(args)
            if args[:2] == ["apt-get", "check"]:
                return {
                    "command": command,
                    "exit_code": 100,
                    "output": (
                        "E: Could not open lock file /var/lib/dpkg/lock-frontend - open (13: Permission denied)\n"
                        "E: Unable to acquire the dpkg frontend lock (/var/lib/dpkg/lock-frontend), are you root?"
                    ),
                    "duration_ms": 1,
                }
            if args[:2] == ["dpkg", "--audit"]:
                return {"command": command, "exit_code": 0, "output": "", "duration_ms": 1}
            if args[:2] == ["findmnt", "--json"]:
                return {
                    "command": command,
                    "exit_code": 0,
                    "output": '{"filesystems":[{"source":"/dev/root","target":"/","fstype":"ext4","options":"rw"}]}',
                    "duration_ms": 1,
                }
            return {"command": command, "exit_code": 0, "output": "", "duration_ms": 1}

        with patch("system_coach_maintenance_manager.diagnostics.platform.system", return_value="Linux"), patch(
            "system_coach_maintenance_manager.diagnostics.shutil.disk_usage", return_value=disk_usage
        ), patch("system_coach_maintenance_manager.diagnostics._read_meminfo", return_value=meminfo), patch(
            "system_coach_maintenance_manager.diagnostics._run_command", side_effect=fake_command
        ), patch(
            "system_coach_maintenance_manager.diagnostics.shutil.which", return_value="/usr/bin/tool"
        ), patch(
            "system_coach_maintenance_manager.diagnostics.socket.getaddrinfo", return_value=[("ok",)]
        ):
            report = collect_diagnostics()

        package_finding = next(finding for finding in report["findings"] if finding["id"] == "package-manager-health")
        self.assertEqual(package_finding["status"], "pass")
        self.assertEqual(package_finding["severity"], "info")
        self.assertFalse(package_finding["can_prepare_action"])
        self.assertTrue(package_finding["evidence"]["non_root_lock_denial"])
        self.assertIn("dpkg --audit", [item["command"] for item in package_finding["commands_run"]])


if __name__ == "__main__":
    unittest.main()
