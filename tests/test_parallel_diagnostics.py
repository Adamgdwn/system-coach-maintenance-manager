"""Tests for Chunk 24: parallel diagnostics, parallel agent probes, and engine status cache."""

from __future__ import annotations

import threading
import unittest
from collections import namedtuple
from unittest.mock import MagicMock, patch

from system_coach_maintenance_manager import ai_engine
from system_coach_maintenance_manager.diagnostics import collect_diagnostics


_DISK_USAGE = namedtuple("usage", ["total", "used", "free"])(total=1000, used=500, free=500)
_MEMINFO = {
    "MemTotal": 2000,
    "MemAvailable": 1600,
    "SwapTotal": 500,
    "SwapFree": 500,
}


def _fake_command(args, timeout=6):
    command = " ".join(args)
    if args[:2] == ["systemctl", "--failed"]:
        return {"command": command, "exit_code": 0, "output": "", "duration_ms": 1}
    if args[:2] == ["journalctl", "-p"]:
        return {"command": command, "exit_code": 0, "output": "-- No entries --", "duration_ms": 1}
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


def _patched_collect():
    """Run collect_diagnostics() with all I/O mocked out."""
    with (
        patch("system_coach_maintenance_manager.diagnostics.shutil.disk_usage", return_value=_DISK_USAGE),
        patch("system_coach_maintenance_manager.diagnostics._read_meminfo", return_value=_MEMINFO),
        patch("system_coach_maintenance_manager.diagnostics._run_command", side_effect=_fake_command),
        patch("system_coach_maintenance_manager.diagnostics.shutil.which", return_value="/usr/bin/tool"),
        patch("system_coach_maintenance_manager.diagnostics.socket.getaddrinfo", return_value=[("ok",)]),
    ):
        return collect_diagnostics()


class TestParallelDiagnosticsResultSet(unittest.TestCase):
    """The parallel result set must match the serial result set on the same mock data."""

    def setUp(self):
        self.report = _patched_collect()

    def test_findings_key_present(self):
        self.assertIn("findings", self.report)

    def test_metrics_key_present(self):
        self.assertIn("metrics", self.report)

    def test_all_expected_finding_ids_present(self):
        ids = {f["id"] for f in self.report["findings"]}
        expected = {
            "diagnostic-readiness",
            "memory-pressure",
            "cpu-load",
            "failed-services",
            "journal-errors",
            "network-basics",
            "package-manager-health",
        }
        self.assertTrue(expected.issubset(ids), f"Missing: {expected - ids}")

    def test_disk_finding_present(self):
        ids = [f["id"] for f in self.report["findings"]]
        self.assertTrue(any(fid.startswith("disk-") for fid in ids))

    def test_memory_metric_populated(self):
        mem = self.report["metrics"]["memory"]
        self.assertEqual(mem["total_bytes"], _MEMINFO["MemTotal"])
        self.assertEqual(mem["available_bytes"], _MEMINFO["MemAvailable"])

    def test_disk_snapshots_in_metrics(self):
        self.assertIsInstance(self.report["metrics"]["disks"], list)
        self.assertGreater(len(self.report["metrics"]["disks"]), 0)

    def test_command_log_populated(self):
        # At least some findings emit commands
        self.assertIsInstance(self.report["command_log"], list)

    def test_generated_at_present(self):
        self.assertIn("generated_at", self.report)

    def test_result_is_deterministic_across_two_calls(self):
        """Calling twice with the same mocks must produce identical finding IDs and statuses."""
        report2 = _patched_collect()
        ids1 = sorted(f["id"] for f in self.report["findings"])
        ids2 = sorted(f["id"] for f in report2["findings"])
        self.assertEqual(ids1, ids2)
        statuses1 = {f["id"]: f["status"] for f in self.report["findings"]}
        statuses2 = {f["id"]: f["status"] for f in report2["findings"]}
        self.assertEqual(statuses1, statuses2)


class TestParallelAgentProbes(unittest.TestCase):
    """build_report() must produce the same result set regardless of execution order."""

    def _make_fake_agent(self, agent_id: str) -> MagicMock:
        agent = MagicMock()
        agent.run.return_value = {"id": agent_id, "findings": [], "commands": []}
        return agent

    def test_all_agent_results_included(self):
        from system_coach_maintenance_manager import server

        fake_agents = [self._make_fake_agent(f"agent-{i}") for i in range(5)]
        with patch("system_coach_maintenance_manager.server.build_agents", return_value=fake_agents), patch(
            "system_coach_maintenance_manager.server.generate_report", side_effect=lambda results: {"results": results}
        ):
            report = server.build_report()

        result_ids = {r["id"] for r in report["results"]}
        expected_ids = {f"agent-{i}" for i in range(5)}
        self.assertEqual(result_ids, expected_ids)

    def test_each_agent_run_called_exactly_once(self):
        from system_coach_maintenance_manager import server

        fake_agents = [self._make_fake_agent(f"agent-{i}") for i in range(4)]
        with patch("system_coach_maintenance_manager.server.build_agents", return_value=fake_agents), patch(
            "system_coach_maintenance_manager.server.generate_report", side_effect=lambda results: {"results": results}
        ):
            server.build_report()

        for agent in fake_agents:
            agent.run.assert_called_once()


class TestEngineStatusCache(unittest.TestCase):
    def setUp(self):
        ai_engine.invalidate_engine_cache()

    def tearDown(self):
        ai_engine.invalidate_engine_cache()

    def _mock_status(self, call_count_holder: list) -> dict:
        call_count_holder.append(1)
        return {
            "available": True,
            "provider": "ollama",
            "models": ["qwen3:8b"],
            "selected_model": "qwen3:8b",
            "message": "Using local model qwen3:8b through Ollama.",
        }

    def test_second_call_within_ttl_does_not_re_fetch(self):
        calls: list[int] = []
        with patch.object(ai_engine, "_fetch_engine_status", side_effect=lambda: self._mock_status(calls)):
            ai_engine.get_engine_status()
            ai_engine.get_engine_status()
        self.assertEqual(len(calls), 1)

    def test_cache_returns_same_object_within_ttl(self):
        with patch.object(ai_engine, "_fetch_engine_status", return_value={"available": True, "models": ["m"]}):
            first = ai_engine.get_engine_status()
            second = ai_engine.get_engine_status()
        self.assertIs(first, second)

    def test_invalidate_forces_re_fetch(self):
        calls: list[int] = []
        with patch.object(ai_engine, "_fetch_engine_status", side_effect=lambda: self._mock_status(calls)):
            ai_engine.get_engine_status()
            ai_engine.invalidate_engine_cache()
            ai_engine.get_engine_status()
        self.assertEqual(len(calls), 2)

    def test_cache_refreshes_after_ttl_expires(self):
        calls: list[int] = []

        def fake_fetch():
            return self._mock_status(calls)

        with patch.object(ai_engine, "_fetch_engine_status", side_effect=fake_fetch):
            ai_engine.get_engine_status()
            # Simulate TTL expiry by winding back the expiry timestamp
            with ai_engine._engine_cache_lock:
                ai_engine._engine_status_expiry = 0.0
            ai_engine.get_engine_status()
        self.assertEqual(len(calls), 2)

    def test_concurrent_calls_fetch_only_once(self):
        """Multiple threads racing on an empty cache must yield only one fetch."""
        calls: list[int] = []

        def slow_fetch():
            import time

            time.sleep(0.02)
            return self._mock_status(calls)

        with patch.object(ai_engine, "_fetch_engine_status", side_effect=slow_fetch):
            threads = [threading.Thread(target=ai_engine.get_engine_status) for _ in range(8)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
