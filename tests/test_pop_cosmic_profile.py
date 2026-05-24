import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from system_coach_maintenance_manager.pop_cosmic_profile import (
    detect_pop_cosmic_environment,
    is_pop_os,
    read_os_release,
)


class PopCosmicProfileTests(unittest.TestCase):
    def test_reads_pop_os_release_fixture(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "os-release"
            path.write_text('ID=pop\nNAME="Pop!_OS"\nVERSION_ID="24.04"\n', encoding="utf-8")

            values = read_os_release(path)

        self.assertEqual(values["ID"], "pop")
        self.assertTrue(is_pop_os(values))

    def test_detects_cosmic_session_without_required_commands(self):
        with patch(
            "system_coach_maintenance_manager.pop_cosmic_profile.read_os_release",
            return_value={"ID": "ubuntu", "NAME": "Ubuntu", "VERSION_ID": "24.04"},
        ), patch.dict(
            "os.environ",
            {
                "XDG_CURRENT_DESKTOP": "COSMIC",
                "XDG_SESSION_TYPE": "wayland",
            },
            clear=True,
        ), patch("system_coach_maintenance_manager.pop_cosmic_profile.shutil.which", return_value=None):
            profile = detect_pop_cosmic_environment()

        self.assertFalse(profile["is_pop_os"])
        self.assertTrue(profile["has_cosmic_signal"])
        self.assertTrue(profile["applicable"])


if __name__ == "__main__":
    unittest.main()
