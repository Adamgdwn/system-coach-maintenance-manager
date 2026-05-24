import json
import os
import tempfile
import unittest
import urllib.error
from subprocess import CompletedProcess
from unittest.mock import patch

from system_coach_maintenance_manager.system_capabilities import detect_system_capabilities


class _FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class SystemCapabilityTests(unittest.TestCase):
    def test_pop_cosmic_machine_enables_pop_agent_and_local_model(self):
        def fake_which(command):
            present = {
                "apt",
                "apt-get",
                "cosmic-randr",
                "cosmic-settings",
                "journalctl",
                "lspci",
                "ollama",
                "pkexec",
                "systemctl",
                "xrandr",
            }
            return f"/usr/bin/{command}" if command in present else None

        with tempfile.TemporaryDirectory() as history_dir, patch.dict(
            os.environ,
            {
                "SYSTEM_COACH_HISTORY_DIR": history_dir,
                "XDG_CURRENT_DESKTOP": "COSMIC",
                "XDG_SESSION_TYPE": "wayland",
                "WAYLAND_DISPLAY": "wayland-0",
            },
            clear=True,
        ), patch("system_coach_maintenance_manager.system_capabilities.platform.system", return_value="Linux"), patch(
            "system_coach_maintenance_manager.system_capabilities.platform.release", return_value="6.8"
        ), patch(
            "system_coach_maintenance_manager.system_capabilities.platform.platform", return_value="Linux-6.8"
        ), patch(
            "system_coach_maintenance_manager.system_capabilities.platform.machine", return_value="x86_64"
        ), patch(
            "system_coach_maintenance_manager.system_capabilities.platform.processor", return_value="x86_64"
        ), patch(
            "system_coach_maintenance_manager.system_capabilities.read_os_release",
            return_value={"ID": "pop", "PRETTY_NAME": "Pop!_OS 24.04 LTS", "VERSION_ID": "24.04"},
        ), patch(
            "system_coach_maintenance_manager.system_capabilities.shutil.which", side_effect=fake_which
        ), patch(
            "system_coach_maintenance_manager.system_capabilities.urllib.request.urlopen",
            return_value=_FakeResponse({"models": [{"name": "qwen3:8b"}, {"name": "gemma4:latest"}]}),
        ), patch(
            "system_coach_maintenance_manager.system_capabilities.subprocess.run",
            return_value=CompletedProcess(
                args=["lspci", "-nn"],
                returncode=0,
                stdout="00:02.0 VGA compatible controller: Intel Corporation Graphics\n",
                stderr="",
            ),
        ):
            profile = detect_system_capabilities()

        surfaces = {item["id"]: item for item in profile["surfaces"]}
        self.assertEqual(profile["onboarding_mode"], "unknown-machine-first-run")
        self.assertEqual(profile["desktop"]["family"], "cosmic")
        self.assertTrue(surfaces["pop-cosmic-agent"]["available"])
        self.assertTrue(surfaces["local-model-coach"]["available"])
        self.assertTrue(profile["display_stack"]["cosmic_tools_available"])
        self.assertIn("docs/pop-cosmic-agent.md", profile["recommended_docs"])
        self.assertEqual(profile["local_storage"]["history_dir"], history_dir)
        self.assertFalse(profile["local_storage"]["repository_storage_allowed"])

    def test_ubuntu_gnome_degrades_pop_agent_to_advisory(self):
        def fake_which(command):
            return f"/usr/bin/{command}" if command in {"apt", "apt-get", "journalctl", "systemctl", "xrandr"} else None

        with patch.dict(
            os.environ,
            {"XDG_CURRENT_DESKTOP": "GNOME", "XDG_SESSION_TYPE": "wayland", "WAYLAND_DISPLAY": "wayland-0"},
            clear=True,
        ), patch("system_coach_maintenance_manager.system_capabilities.platform.system", return_value="Linux"), patch(
            "system_coach_maintenance_manager.system_capabilities.platform.release", return_value="6.8"
        ), patch(
            "system_coach_maintenance_manager.system_capabilities.platform.platform", return_value="Linux-6.8"
        ), patch(
            "system_coach_maintenance_manager.system_capabilities.read_os_release",
            return_value={
                "ID": "ubuntu",
                "ID_LIKE": "debian",
                "PRETTY_NAME": "Ubuntu 24.04 LTS",
                "VERSION_ID": "24.04",
            },
        ), patch(
            "system_coach_maintenance_manager.system_capabilities.shutil.which", side_effect=fake_which
        ), patch(
            "system_coach_maintenance_manager.system_capabilities.urllib.request.urlopen",
            side_effect=urllib.error.URLError("down"),
        ):
            profile = detect_system_capabilities()

        surfaces = {item["id"]: item for item in profile["surfaces"]}
        self.assertEqual(profile["desktop"]["family"], "gnome")
        self.assertFalse(surfaces["pop-cosmic-agent"]["available"])
        self.assertTrue(surfaces["request-desk"]["available"])
        self.assertFalse(surfaces["local-model-coach"]["available"])
        self.assertIn("docs/setup-linux.md", profile["recommended_docs"])
        self.assertNotIn("docs/pop-cosmic-agent.md", profile["recommended_docs"])

    def test_windows_browser_mode_surfaces_portable_paths(self):
        def fake_which(command):
            return f"C:/Windows/System32/{command}.exe" if command in {"powershell", "winget", "wevtutil"} else None

        with patch.dict(os.environ, {"SESSIONNAME": "Console"}, clear=True), patch(
            "system_coach_maintenance_manager.system_capabilities.platform.system", return_value="Windows"
        ), patch(
            "system_coach_maintenance_manager.system_capabilities.platform.release", return_value="11"
        ), patch(
            "system_coach_maintenance_manager.system_capabilities.platform.version", return_value="10.0.22631"
        ), patch(
            "system_coach_maintenance_manager.system_capabilities.platform.platform", return_value="Windows-11"
        ), patch(
            "system_coach_maintenance_manager.system_capabilities.shutil.which", side_effect=fake_which
        ), patch(
            "system_coach_maintenance_manager.system_capabilities.urllib.request.urlopen",
            side_effect=urllib.error.URLError("down"),
        ):
            profile = detect_system_capabilities()

        surfaces = {item["id"]: item for item in profile["surfaces"]}
        self.assertEqual(profile["desktop"]["family"], "windows-shell")
        self.assertTrue(surfaces["maintenance-diagnostics"]["available"])
        self.assertTrue(surfaces["elevated-runner"]["available"])
        self.assertFalse(surfaces["pop-cosmic-agent"]["available"])
        self.assertIn("docs/setup-windows-browser.md", profile["recommended_docs"])


if __name__ == "__main__":
    unittest.main()
