import unittest
from subprocess import CompletedProcess
from unittest.mock import patch

from system_coach_maintenance_manager.request_evidence import collect_request_evidence


class RequestEvidenceTests(unittest.TestCase):
    def _which(self, command):
        return f"/usr/bin/{command}"

    def test_collects_display_dock_evidence_without_user_inventory(self):
        with patch("system_coach_maintenance_manager.request_evidence.shutil.which", side_effect=self._which), patch(
            "system_coach_maintenance_manager.request_evidence.subprocess.run",
            return_value=CompletedProcess(args=[], returncode=0, stdout="Samsung C27F390\nDell DisplayLink D6000\n", stderr=""),
        ):
            evidence = collect_request_evidence(
                "My far right screen through the Dell dock is rotated and the cursor is jittery.",
                os_name="Linux",
                desktop_hint="COSMIC",
            )

        self.assertIn("display-dock", evidence["scopes"])
        commands = [item["command"] for item in evidence["commands"]]
        self.assertIn("cosmic-randr list", commands)
        self.assertIn("lsusb", commands)
        self.assertIn("lspci", commands)

    def test_collects_multiple_relevant_scopes_for_general_requests(self):
        with patch("system_coach_maintenance_manager.request_evidence.shutil.which", side_effect=self._which), patch(
            "system_coach_maintenance_manager.request_evidence.subprocess.run",
            return_value=CompletedProcess(args=[], returncode=0, stdout="ok\n", stderr=""),
        ):
            evidence = collect_request_evidence(
                "My computer is slow, Docker may be full, and DNS seems broken.",
                os_name="Linux",
            )

        self.assertIn("slow-computer", evidence["scopes"])
        self.assertIn("docker-cleanup", evidence["scopes"])
        self.assertIn("network-dns", evidence["scopes"])
        commands = [item["command"] for item in evidence["commands"]]
        self.assertIn("docker system df", commands)
        self.assertIn("ip route", commands)
        self.assertIn("uptime", commands)

    def test_collects_pop_cosmic_scope_for_cosmic_requests(self):
        with patch("system_coach_maintenance_manager.request_evidence.Path.exists", return_value=True), patch(
            "system_coach_maintenance_manager.request_evidence.shutil.which", side_effect=self._which
        ), patch(
            "system_coach_maintenance_manager.request_evidence.subprocess.run",
            return_value=CompletedProcess(args=[], returncode=0, stdout="cosmic-comp display error\n", stderr=""),
        ):
            evidence = collect_request_evidence(
                "COSMIC panel freezes on Pop OS after suspend.",
                os_name="Linux",
                desktop_hint="COSMIC",
            )

        self.assertIn("pop-cosmic", evidence["scopes"])
        commands = [item["command"] for item in evidence["commands"]]
        self.assertIn("systemctl --user --failed --no-legend --plain", commands)
        self.assertIn("journalctl --user -b -n 300 --no-pager", commands)
        self.assertIn("apt list --upgradable", commands)


if __name__ == "__main__":
    unittest.main()
