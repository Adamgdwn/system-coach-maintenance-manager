"""Tests for autonomy_controls.py — gate logic and depth resolution."""

from __future__ import annotations

import tempfile
import textwrap
import unittest
from pathlib import Path

from system_coach_maintenance_manager import autonomy_controls


def _write_yaml(content: str) -> Path:
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
    tmp.write(textwrap.dedent(content))
    tmp.flush()
    return Path(tmp.name)


class TestLoadAutonomySettings(unittest.TestCase):
    def test_reads_a1_d1(self):
        path = _write_yaml("""\
            agent_controls:
              agent_autonomy_level: A1
              agent_depth_level: D1
        """)
        settings = autonomy_controls.load_autonomy_settings(path)
        self.assertEqual(settings["agent_autonomy_level"], "A1")
        self.assertEqual(settings["agent_depth_level"], "D1")

    def test_reads_a3_d2(self):
        path = _write_yaml("""\
            agent_controls:
              agent_autonomy_level: A3
              agent_depth_level: D2
        """)
        settings = autonomy_controls.load_autonomy_settings(path)
        self.assertEqual(settings["agent_autonomy_level"], "A3")
        self.assertEqual(settings["agent_depth_level"], "D2")

    def test_missing_file_defaults_to_a0_d1(self):
        settings = autonomy_controls.load_autonomy_settings(Path("/nonexistent/project-control.yaml"))
        self.assertEqual(settings["agent_autonomy_level"], "A0")
        self.assertEqual(settings["agent_depth_level"], "D1")

    def test_unknown_level_defaults_to_a0(self):
        path = _write_yaml("""\
            agent_autonomy_level: X9
            agent_depth_level: D1
        """)
        settings = autonomy_controls.load_autonomy_settings(path)
        self.assertEqual(settings["agent_autonomy_level"], "A0")


class TestExecutionAllowed(unittest.TestCase):
    def _path_for(self, level: str) -> Path:
        return _write_yaml(f"agent_autonomy_level: {level}\nagent_depth_level: D1\n")

    def test_a0_blocks_execution(self):
        self.assertFalse(autonomy_controls.execution_allowed(self._path_for("A0")))

    def test_a1_allows_execution(self):
        self.assertTrue(autonomy_controls.execution_allowed(self._path_for("A1")))

    def test_a2_allows_execution(self):
        self.assertTrue(autonomy_controls.execution_allowed(self._path_for("A2")))

    def test_a3_allows_execution(self):
        self.assertTrue(autonomy_controls.execution_allowed(self._path_for("A3")))

    def test_a4_allows_execution(self):
        self.assertTrue(autonomy_controls.execution_allowed(self._path_for("A4")))

    def test_missing_file_blocks_execution(self):
        self.assertFalse(autonomy_controls.execution_allowed(Path("/nonexistent/project-control.yaml")))


class TestCanAutoExecute(unittest.TestCase):
    def _path_for(self, level: str) -> Path:
        return _write_yaml(f"agent_autonomy_level: {level}\nagent_depth_level: D1\n")

    def test_a0_never_auto_executes(self):
        path = self._path_for("A0")
        for tier in ("low", "medium", "high"):
            self.assertFalse(autonomy_controls.can_auto_execute(tier, path), tier)

    def test_a1_never_auto_executes(self):
        path = self._path_for("A1")
        for tier in ("low", "medium", "high"):
            self.assertFalse(autonomy_controls.can_auto_execute(tier, path), tier)

    def test_a2_auto_executes_low_only(self):
        path = self._path_for("A2")
        self.assertTrue(autonomy_controls.can_auto_execute("low", path))
        self.assertFalse(autonomy_controls.can_auto_execute("medium", path))
        self.assertFalse(autonomy_controls.can_auto_execute("high", path))

    def test_a3_auto_executes_low_and_medium(self):
        path = self._path_for("A3")
        self.assertTrue(autonomy_controls.can_auto_execute("low", path))
        self.assertTrue(autonomy_controls.can_auto_execute("medium", path))
        self.assertFalse(autonomy_controls.can_auto_execute("high", path))

    def test_a4_auto_executes_all_tiers(self):
        path = self._path_for("A4")
        for tier in ("low", "medium", "high"):
            self.assertTrue(autonomy_controls.can_auto_execute(tier, path), tier)

    def test_tier_case_insensitive(self):
        path = self._path_for("A2")
        self.assertTrue(autonomy_controls.can_auto_execute("LOW", path))
        self.assertFalse(autonomy_controls.can_auto_execute("HIGH", path))


class TestMaxDepth(unittest.TestCase):
    def _path_for(self, level: str) -> Path:
        return _write_yaml(f"agent_autonomy_level: A1\nagent_depth_level: {level}\n")

    def test_d1_returns_1(self):
        self.assertEqual(autonomy_controls.max_depth(self._path_for("D1")), 1)

    def test_d2_returns_2(self):
        self.assertEqual(autonomy_controls.max_depth(self._path_for("D2")), 2)

    def test_d3_returns_3(self):
        self.assertEqual(autonomy_controls.max_depth(self._path_for("D3")), 3)

    def test_d4_returns_4(self):
        self.assertEqual(autonomy_controls.max_depth(self._path_for("D4")), 4)

    def test_unknown_depth_defaults_to_1(self):
        path = _write_yaml("agent_autonomy_level: A1\nagent_depth_level: X9\n")
        self.assertEqual(autonomy_controls.max_depth(path), 1)

    def test_missing_file_defaults_to_1(self):
        self.assertEqual(autonomy_controls.max_depth(Path("/nonexistent/project-control.yaml")), 1)


if __name__ == "__main__":
    unittest.main()
