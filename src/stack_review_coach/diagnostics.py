"""Read-only system maintenance diagnostics."""

from __future__ import annotations

import datetime as dt
import ctypes
import os
import platform
from pathlib import Path
import shutil
import socket
import subprocess
import time


DIAGNOSTIC_COMMAND_TIMEOUT = 6


def _now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def _run_command(args: list[str], timeout: int = DIAGNOSTIC_COMMAND_TIMEOUT) -> dict:
    started = time.time()
    try:
        completed = subprocess.run(
            args,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = (completed.stdout or completed.stderr).strip()
        return {
            "command": " ".join(args),
            "exit_code": completed.returncode,
            "output": output[:2000],
            "duration_ms": int((time.time() - started) * 1000),
        }
    except FileNotFoundError:
        return {
            "command": " ".join(args),
            "exit_code": 127,
            "output": "Command is not available on this machine.",
            "duration_ms": int((time.time() - started) * 1000),
        }
    except subprocess.TimeoutExpired:
        return {
            "command": " ".join(args),
            "exit_code": 124,
            "output": "Timed out while collecting this read-only diagnostic.",
            "duration_ms": int((time.time() - started) * 1000),
        }


def _command_available(command: str) -> dict:
    resolved = shutil.which(command)
    return {"command": command, "present": resolved is not None, "path": resolved}


def _desktop_context(os_name: str) -> dict:
    if os_name.lower() == "linux":
        return {
            "current_desktop": os.environ.get("XDG_CURRENT_DESKTOP", "unknown"),
            "desktop_session": os.environ.get("DESKTOP_SESSION", "unknown"),
            "session_type": os.environ.get("XDG_SESSION_TYPE", "unknown"),
        }
    if os_name.lower().startswith("win"):
        return {
            "current_desktop": "Windows Shell",
            "desktop_session": os.environ.get("SESSIONNAME", "unknown"),
            "session_type": "windows",
        }
    return {"current_desktop": "unknown", "desktop_session": "unknown", "session_type": "unknown"}


def _read_meminfo(path: Path = Path("/proc/meminfo")) -> dict[str, int]:
    values: dict[str, int] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        if ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        parts = raw_value.strip().split()
        if not parts:
            continue
        try:
            values[key] = int(parts[0]) * 1024
        except ValueError:
            continue
    return values


def _read_windows_memory() -> dict[str, int]:
    class MemoryStatus(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    status = MemoryStatus()
    status.dwLength = ctypes.sizeof(MemoryStatus)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):  # type: ignore[attr-defined]
        return {}
    return {
        "MemTotal": int(status.ullTotalPhys),
        "MemAvailable": int(status.ullAvailPhys),
        "SwapTotal": int(status.ullTotalPageFile),
        "SwapFree": int(status.ullAvailPageFile),
    }


def _memory_values(os_name: str) -> dict[str, int]:
    if os_name.lower().startswith("win"):
        return _read_windows_memory()
    return _read_meminfo()


def _disk_paths(os_name: str) -> list[Path]:
    home = Path.home()
    candidates = [home]
    if os_name.lower().startswith("win"):
        anchor = home.anchor or "C:\\"
        candidates.insert(0, Path(anchor))
    else:
        candidates.insert(0, Path("/"))

    resolved_paths = []
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if resolved not in resolved_paths:
            resolved_paths.append(resolved)
    return resolved_paths


def _disk_snapshot(path: Path) -> dict:
    resolved = path.expanduser().resolve()
    usage = shutil.disk_usage(resolved)
    used_percent = round((usage.used / usage.total) * 100, 2) if usage.total else 0
    return {
        "path": str(resolved),
        "total_bytes": usage.total,
        "used_bytes": usage.used,
        "free_bytes": usage.free,
        "used_percent": used_percent,
    }


def _mount_snapshot(path: Path) -> dict:
    if not shutil.which("findmnt"):
        return {"path": str(path), "source": None, "target": None, "fstype": None, "options": [], "available": False}

    result = _run_command(["findmnt", "--json", "-T", str(path)])
    if result["exit_code"] != 0:
        return {
            "path": str(path),
            "source": None,
            "target": None,
            "fstype": None,
            "options": [],
            "available": True,
            "error": result["output"],
        }

    import json

    try:
        payload = json.loads(result["output"])
    except json.JSONDecodeError:
        return {
            "path": str(path),
            "source": None,
            "target": None,
            "fstype": None,
            "options": [],
            "available": True,
            "error": "findmnt returned output that could not be parsed.",
        }

    filesystems = payload.get("filesystems") or []
    if not filesystems:
        return {"path": str(path), "source": None, "target": None, "fstype": None, "options": [], "available": True}

    filesystem = filesystems[0]
    return {
        "path": str(path),
        "source": filesystem.get("source"),
        "target": filesystem.get("target"),
        "fstype": filesystem.get("fstype"),
        "options": filesystem.get("options", "").split(",") if filesystem.get("options") else [],
        "available": True,
    }


def _finding(
    *,
    check_id: str,
    title: str,
    category: str,
    status: str,
    severity: str,
    summary: str,
    evidence: dict,
    next_steps: list[str],
    commands: list[dict] | None = None,
    requires_privilege: bool = False,
    can_prepare_action: bool = False,
) -> dict:
    return {
        "id": check_id,
        "title": title,
        "category": category,
        "status": status,
        "severity": severity,
        "summary": summary,
        "evidence": evidence,
        "recommended_next_steps": next_steps,
        "commands_run": commands or [],
        "requires_privilege": requires_privilege,
        "can_prepare_action": can_prepare_action,
    }


def _disk_findings(snapshots: list[dict]) -> list[dict]:
    findings = []
    for snapshot in snapshots:
        used = snapshot["used_percent"]
        if used >= 95:
            status = "fail"
            severity = "critical"
            summary = f"{snapshot['path']} is critically full at {used}% used."
        elif used >= 85:
            status = "warn"
            severity = "warning"
            summary = f"{snapshot['path']} is under disk pressure at {used}% used."
        else:
            status = "pass"
            severity = "info"
            summary = f"{snapshot['path']} has acceptable free space at {used}% used."

        findings.append(
            _finding(
                check_id=f"disk-{snapshot['path'].replace('/', '_') or 'root'}",
                title=f"Disk Space: {snapshot['path']}",
                category="disk",
                status=status,
                severity=severity,
                summary=summary,
                evidence=snapshot,
                next_steps=[
                    "Review large files and caches before deleting anything.",
                    "Prepare a cleanup plan instead of running broad cleanup commands automatically.",
                ],
                can_prepare_action=status in {"warn", "fail"},
            )
        )
    return findings


def _memory_finding(meminfo: dict[str, int]) -> dict:
    total = meminfo.get("MemTotal", 0)
    available = meminfo.get("MemAvailable", 0)
    available_percent = round((available / total) * 100, 2) if total else 0
    swap_total = meminfo.get("SwapTotal", 0)
    swap_free = meminfo.get("SwapFree", 0)
    swap_used = max(swap_total - swap_free, 0)

    if not total:
        return _finding(
            check_id="memory-pressure",
            title="Memory Pressure",
            category="performance",
            status="unknown",
            severity="info",
            summary="Memory information is unavailable on this operating system.",
            evidence={},
            next_steps=["Use the operating system's activity monitor to inspect memory pressure manually."],
        )

    if available_percent < 5:
        status = "fail"
        severity = "critical"
        summary = f"Available memory is critically low at {available_percent}%."
    elif available_percent < 12:
        status = "warn"
        severity = "warning"
        summary = f"Available memory is low at {available_percent}%."
    else:
        status = "pass"
        severity = "info"
        summary = f"Memory pressure looks normal with {available_percent}% available."

    return _finding(
        check_id="memory-pressure",
        title="Memory Pressure",
        category="performance",
        status=status,
        severity=severity,
        summary=summary,
        evidence={
            "total_bytes": total,
            "available_bytes": available,
            "available_percent": available_percent,
            "swap_total_bytes": swap_total,
            "swap_used_bytes": swap_used,
        },
        next_steps=[
            "Close heavy applications before changing system settings.",
            "Use process-level tools to identify sustained memory consumers.",
        ],
        can_prepare_action=False,
    )


def _load_finding() -> dict:
    cpu_count = os.cpu_count() or 1
    try:
        one_min, five_min, fifteen_min = os.getloadavg()
    except OSError:
        return _finding(
            check_id="cpu-load",
            title="CPU Load",
            category="performance",
            status="unknown",
            severity="info",
            summary="CPU load averages are unavailable on this operating system.",
            evidence={"cpu_count": cpu_count},
            next_steps=["Use the operating system's performance monitor to inspect CPU activity."],
        )

    load_ratio = round(one_min / cpu_count, 2)
    if load_ratio >= 2:
        status = "fail"
        severity = "critical"
        summary = f"One-minute load is very high for {cpu_count} CPU(s)."
    elif load_ratio >= 1:
        status = "warn"
        severity = "warning"
        summary = f"One-minute load is elevated for {cpu_count} CPU(s)."
    else:
        status = "pass"
        severity = "info"
        summary = f"CPU load looks normal for {cpu_count} CPU(s)."

    return _finding(
        check_id="cpu-load",
        title="CPU Load",
        category="performance",
        status=status,
        severity=severity,
        summary=summary,
        evidence={
            "cpu_count": cpu_count,
            "one_min": round(one_min, 2),
            "five_min": round(five_min, 2),
            "fifteen_min": round(fifteen_min, 2),
            "one_min_per_cpu": load_ratio,
        },
        next_steps=[
            "Compare load with process activity before stopping anything.",
            "If high load persists, inspect top CPU consumers and recent service errors.",
        ],
    )


def _failed_services_finding(os_name: str) -> dict:
    if os_name.lower().startswith("win"):
        return _finding(
            check_id="failed-services",
            title="Failed Services",
            category="services",
            status="unknown",
            severity="info",
            summary="Windows service failure state is not inferred from service listings yet.",
            evidence={"service_manager": "windows-service-control"},
            next_steps=[
                "Use Event Viewer or the critical event log finding to inspect service failures.",
                "Prepare a named-service plan before restarting or changing Windows services.",
            ],
        )

    if not shutil.which("systemctl"):
        return _finding(
            check_id="failed-services",
            title="Failed Services",
            category="services",
            status="unknown",
            severity="info",
            summary="systemctl is not available, so service state was not inspected.",
            evidence={"systemctl_available": False},
            next_steps=["Use the service manager for this operating system to inspect failed services."],
        )

    command = _run_command(["systemctl", "--failed", "--no-legend", "--plain"])
    if command["exit_code"] != 0:
        return _finding(
            check_id="failed-services",
            title="Failed Services",
            category="services",
            status="unknown",
            severity="warning",
            summary="systemctl was available, but failed service inspection did not complete cleanly.",
            evidence={"error": command["output"]},
            next_steps=["Run `systemctl --failed` manually and inspect any permission or session errors."],
            commands=[command],
        )

    failed_lines = [line for line in command["output"].splitlines() if line.strip()]
    failed_count = len(failed_lines)
    if failed_count >= 4:
        status = "fail"
        severity = "critical"
        summary = f"{failed_count} failed systemd service(s) were detected."
    elif failed_count:
        status = "warn"
        severity = "warning"
        summary = f"{failed_count} failed systemd service(s) were detected."
    else:
        status = "pass"
        severity = "info"
        summary = "No failed systemd services were reported."

    return _finding(
        check_id="failed-services",
        title="Failed Services",
        category="services",
        status=status,
        severity=severity,
        summary=summary,
        evidence={"failed_count": failed_count, "services": failed_lines[:12]},
        next_steps=[
            "Open service status details before restarting or disabling anything.",
            "Prepare a per-service plan if a failed service affects normal work.",
        ],
        commands=[command],
        can_prepare_action=failed_count > 0,
    )


def _journal_finding(os_name: str) -> dict:
    if os_name.lower().startswith("win"):
        if not shutil.which("wevtutil"):
            return _finding(
                check_id="journal-errors",
                title="Recent Critical Logs",
                category="logs",
                status="unknown",
                severity="info",
                summary="wevtutil is not available, so Windows system event errors were not inspected.",
                evidence={"wevtutil_available": False},
                next_steps=["Use Event Viewer to inspect recent critical and error events."],
            )

        command = _run_command(
            [
                "wevtutil",
                "qe",
                "System",
                "/q:*[System[(Level=1 or Level=2)]]",
                "/c:10",
                "/f:text",
                "/rd:true",
            ]
        )
        if command["exit_code"] != 0:
            return _finding(
                check_id="journal-errors",
                title="Recent Critical Logs",
                category="logs",
                status="unknown",
                severity="warning",
                summary="Windows event log inspection did not complete cleanly.",
                evidence={"error": command["output"]},
                next_steps=["Open Event Viewer and inspect recent System log critical/error entries."],
                commands=[command],
            )

        lines = [line for line in command["output"].splitlines() if line.strip()]
        status = "warn" if lines else "pass"
        severity = "warning" if lines else "info"
        summary = (
            f"Recent Windows System event errors were found in {len(lines)} output line(s)."
            if lines
            else "No recent Windows System critical/error events were returned by the bounded query."
        )
        return _finding(
            check_id="journal-errors",
            title="Recent Critical Logs",
            category="logs",
            status=status,
            severity=severity,
            summary=summary,
            evidence={"line_count": len(lines), "sample": lines[:16]},
            next_steps=[
                "Open Event Viewer for full context before restarting services or changing drivers.",
                "Group repeated event sources before preparing a repair plan.",
            ],
            commands=[command],
            can_prepare_action=bool(lines),
        )

    if not shutil.which("journalctl"):
        return _finding(
            check_id="journal-errors",
            title="Recent Critical Logs",
            category="logs",
            status="unknown",
            severity="info",
            summary="journalctl is not available, so system journal errors were not inspected.",
            evidence={"journalctl_available": False},
            next_steps=["Use this operating system's log viewer to inspect recent critical errors."],
        )

    command = _run_command(["journalctl", "-p", "3", "-n", "25", "--no-pager"])
    if command["exit_code"] != 0:
        return _finding(
            check_id="journal-errors",
            title="Recent Critical Logs",
            category="logs",
            status="unknown",
            severity="warning",
            summary="journalctl was available, but recent critical log inspection did not complete cleanly.",
            evidence={"error": command["output"]},
            next_steps=["Run `journalctl -p 3 -n 25 --no-pager` manually to inspect access or log errors."],
            commands=[command],
        )

    lines = [line for line in command["output"].splitlines() if line.strip() and "-- No entries --" not in line]
    if lines:
        status = "warn"
        severity = "warning"
        summary = f"{len(lines)} recent critical journal line(s) were found."
    else:
        status = "pass"
        severity = "info"
        summary = "No recent critical journal entries were reported."

    return _finding(
        check_id="journal-errors",
        title="Recent Critical Logs",
        category="logs",
        status=status,
        severity=severity,
        summary=summary,
        evidence={"line_count": len(lines), "sample": lines[:8]},
        next_steps=[
            "Group repeated log lines by service or device before taking action.",
            "Use log evidence to prepare targeted troubleshooting rather than broad cleanup.",
        ],
        commands=[command],
        can_prepare_action=bool(lines),
    )


def _network_finding(os_name: str) -> dict:
    commands = []
    windows = os_name.lower().startswith("win")
    route_tool = "route" if windows else "ip"
    route_available = shutil.which(route_tool) is not None
    route_output = None
    if route_available:
        route_command = _run_command(["route", "print", "0.0.0.0"] if windows else ["ip", "route", "show", "default"])
        commands.append(route_command)
        route_output = route_command["output"]

    dns_ok = False
    dns_error = None
    previous_timeout = socket.getdefaulttimeout()
    try:
        socket.setdefaulttimeout(3)
        socket.getaddrinfo("example.com", 443)
        dns_ok = True
    except OSError as exc:
        dns_error = str(exc)
    finally:
        socket.setdefaulttimeout(previous_timeout)

    has_default_route = bool(route_output and route_output.strip())
    if has_default_route and dns_ok:
        status = "pass"
        severity = "info"
        summary = "Default route and DNS resolution look available."
    elif not has_default_route:
        status = "warn"
        severity = "warning"
        summary = "No default network route was detected."
    else:
        status = "warn"
        severity = "warning"
        summary = "A default route exists, but DNS resolution did not succeed."

    return _finding(
        check_id="network-basics",
        title="Network Basics",
        category="network",
        status=status,
        severity=severity,
        summary=summary,
        evidence={
            "ip_available": route_available,
            "route_tool": route_tool,
            "default_route_detected": has_default_route,
            "default_route": route_output,
            "dns_probe_host": "example.com",
            "dns_resolution_ok": dns_ok,
            "dns_error": dns_error,
        },
        next_steps=[
            "Inspect default route, DNS settings, and local network connection before changing configuration.",
            "Prepare a network troubleshooting plan if both route and DNS evidence point to a problem.",
        ],
        commands=commands,
        can_prepare_action=status != "pass",
    )


def _package_finding(os_name: str) -> dict:
    candidate_managers = ("winget", "choco") if os_name.lower().startswith("win") else ("apt-get", "dnf", "pacman")
    managers = [_command_available(command) for command in candidate_managers]
    present = [manager for manager in managers if manager["present"]]
    if not present:
        return _finding(
            check_id="package-manager-health",
            title="Package Manager Health",
            category="packages",
            status="unknown",
            severity="info",
            summary="No supported package manager health probe was detected.",
            evidence={"managers": managers},
            next_steps=["Use this system's package manager to verify package database health manually."],
        )

    manager = present[0]["command"]
    if manager == "apt-get":
        command = _run_command(["apt-get", "check"])
    elif manager == "dnf":
        command = _run_command(["dnf", "check"])
    elif manager == "winget":
        command = _run_command(["winget", "--info"])
    elif manager == "choco":
        command = _run_command(["choco", "--version"])
    else:
        command = _run_command(["pacman", "-Dk"])

    status = "pass" if command["exit_code"] == 0 else "warn"
    severity = "info" if status == "pass" else "warning"
    summary = (
        f"{manager} package health check completed cleanly."
        if status == "pass"
        else f"{manager} package health check reported a problem."
    )

    return _finding(
        check_id="package-manager-health",
        title="Package Manager Health",
        category="packages",
        status=status,
        severity=severity,
        summary=summary,
        evidence={"manager": manager, "output": command["output"][:800]},
        next_steps=[
            "Review package-manager output before installing, removing, or repairing packages.",
            "Prepare an approved package repair plan only after the exact issue is clear.",
        ],
        commands=[command],
        can_prepare_action=status != "pass",
    )


def _doctor_finding(commands: list[dict]) -> dict:
    missing = [item["command"] for item in commands if not item["present"]]
    if missing:
        status = "warn"
        severity = "warning"
        summary = f"{len(missing)} optional diagnostic command(s) are unavailable."
    else:
        status = "pass"
        severity = "info"
        summary = "Core diagnostic commands are available."
    return _finding(
        check_id="diagnostic-readiness",
        title="Diagnostic Readiness",
        category="doctor",
        status=status,
        severity=severity,
        summary=summary,
        evidence={"commands": commands, "missing": missing},
        next_steps=[
            "Unavailable commands reduce diagnostic coverage but should not block read-only checks.",
            "Install missing tools only when they are needed for a specific troubleshooting path.",
        ],
    )


def collect_diagnostics() -> dict:
    """Collect read-only local maintenance diagnostics."""

    os_name = platform.system() or "Unknown"
    disk_paths = _disk_paths(os_name)

    disk_snapshots = [_disk_snapshot(path) for path in disk_paths]
    mounts = [_mount_snapshot(path) for path in disk_paths]
    meminfo = _memory_values(os_name)
    readiness_commands = ("wevtutil", "route", "winget") if os_name.lower().startswith("win") else (
        "findmnt",
        "systemctl",
        "journalctl",
        "ip",
    )
    command_readiness = [_command_available(command) for command in readiness_commands]

    findings = [
        _doctor_finding(command_readiness),
        *_disk_findings(disk_snapshots),
        _memory_finding(meminfo),
        _load_finding(),
        _failed_services_finding(os_name),
        _journal_finding(os_name),
        _network_finding(os_name),
        _package_finding(os_name),
    ]

    command_log = []
    for finding in findings:
        command_log.extend(finding.get("commands_run", []))

    return {
        "generated_at": _now(),
        "metrics": {
            "platform": {"os": os_name, "release": platform.release()},
            "desktop": _desktop_context(os_name),
            "disks": disk_snapshots,
            "mounts": mounts,
            "memory": {
                "total_bytes": meminfo.get("MemTotal", 0),
                "available_bytes": meminfo.get("MemAvailable", 0),
                "swap_total_bytes": meminfo.get("SwapTotal", 0),
                "swap_free_bytes": meminfo.get("SwapFree", 0),
            },
        },
        "findings": findings,
        "command_log": command_log,
    }
