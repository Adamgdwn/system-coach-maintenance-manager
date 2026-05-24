import unittest
from subprocess import CompletedProcess
from unittest.mock import patch

from system_coach_maintenance_manager.pop_cosmic_deep_scan import (
    redact_tokens,
    redact_user_paths,
    run_pop_cosmic_deep_scan,
)


class PopCosmicDeepScanTests(unittest.TestCase):
    def test_redacts_user_paths_and_tokens(self):
        text = redact_user_paths("/home/alice/.config/cosmic/config.ron")
        self.assertIn("/home/$USER", text)
        self.assertIn("[REDACTED]", redact_tokens("password=super-secret"))

    def test_standard_scan_runs_only_read_only_commands(self):
        def fake_which(command):
            return f"/usr/bin/{command}"

        def fake_run(args, **kwargs):
            command = " ".join(args)
            return CompletedProcess(args=args, returncode=0, stdout=f"{command} ok\n", stderr="")

        with patch(
            "system_coach_maintenance_manager.pop_cosmic_profile.read_os_release",
            return_value={"ID": "pop", "NAME": "Pop!_OS", "PRETTY_NAME": "Pop!_OS 24.04 LTS", "VERSION_ID": "24.04"},
        ), patch.dict(
            "os.environ",
            {"XDG_CURRENT_DESKTOP": "COSMIC", "XDG_SESSION_TYPE": "wayland"},
            clear=True,
        ), patch("system_coach_maintenance_manager.pop_cosmic_profile.shutil.which", side_effect=fake_which), patch(
            "system_coach_maintenance_manager.pop_cosmic_deep_scan.shutil.which", side_effect=fake_which
        ), patch(
            "system_coach_maintenance_manager.pop_cosmic_profile.subprocess.run", side_effect=fake_run
        ), patch(
            "system_coach_maintenance_manager.pop_cosmic_deep_scan.subprocess.run", side_effect=fake_run
        ):
            scan = run_pop_cosmic_deep_scan("standard")

        self.assertTrue(scan["applicable"])
        self.assertEqual(scan["scope"], "standard")
        commands = []
        for group in scan["groups"].values():
            if isinstance(group, dict):
                commands.extend(item.get("command", "") for item in group.get("commands", []))
        command_blob = "\n".join(commands)
        self.assertIn("apt-get check", command_blob)
        self.assertNotIn("full-upgrade", command_blob)
        self.assertNotIn(" install ", command_blob)


if __name__ == "__main__":
    unittest.main()
