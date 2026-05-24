"""Bounded Pop!_OS and COSMIC deep-scan evidence collection."""

from __future__ import annotations

import datetime as dt
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
from typing import Any

from .pop_cosmic_profile import detect_pop_cosmic_environment


SCAN_TIMEOUT = 8
UPDATE_TIMEOUT = 18
MAX_OUTPUT_CHARS = 8000
LOG_KEYWORDS = (
    "cosmic",
    "cosmic-comp",
    "cosmic-panel",
    "cosmic-session",
    "compositor",
    "wayland",
    "xwayland",
    "smithay",
    "panel",
    "launcher",
    "workspace",
    "display",
    "monitor",
    "cursor",
    "pointer",
    "input",
    "dock",
    "displaylink",
    "drm",
    "egl",
    "nvidia",
    "failed",
    "error",
    "crash",
    "panic",
    "segfault",
    "timeout",
)
SCAN_SCOPES = {"standard", "display", "updates", "full"}


def _now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def redact_user_paths(text: str) -> str:
    home = str(Path.home())
    if home and home != "/":
        text = text.replace(home, "$HOME")
    return re.sub(r"/home/[^/\s:]+", "/home/$USER", text)


def redact_hostnames(text: str) -> str:
    hostname = os.uname().nodename if hasattr(os, "uname") else ""
    if hostname:
        text = text.replace(hostname, "$HOST")
    return text


def redact_tokens(text: str) -> str:
    patterns = (
        r"(?i)(token|secret|password|passwd|apikey|api_key|authorization)(\s*[=:]\s*)\S+",
        r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+",
    )
    for pattern in patterns:
        text = re.sub(pattern, lambda match: f"{match.group(1)}{match.group(2) if len(match.groups()) > 1 else ''}[REDACTED]", text)
    return text


def cap_output(text: str, max_chars: int = MAX_OUTPUT_CHARS) -> str:
    return text[:max_chars]


def sanitize_output(text: str, max_chars: int = MAX_OUTPUT_CHARS) -> str:
    return cap_output(redact_tokens(redact_hostnames(redact_user_paths(text))), max_chars=max_chars)


def _run_read_only(args: list[str], *, timeout: int = SCAN_TIMEOUT) -> dict:
    started = time.time()
    try:
        completed = subprocess.run(args, check=False, capture_output=True, text=True, timeout=timeout)
        output = (completed.stdout or completed.stderr or "").strip()
        return {
            "command": " ".join(args),
            "exit_code": completed.returncode,
            "output": sanitize_output(output),
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
            "output": "Timed out while collecting bounded Pop!_OS/COSMIC evidence.",
            "duration_ms": int((time.time() - started) * 1000),
        }


def _available_command(args: list[str]) -> bool:
    return shutil.which(args[0]) is not None


def _run_available(commands: list[list[str]], *, timeout: int = SCAN_TIMEOUT) -> list[dict]:
    return [_run_read_only(args, timeout=timeout) for args in commands if _available_command(args)]


def _filter_log_command(command: dict, keywords: tuple[str, ...] = LOG_KEYWORDS) -> dict:
    matches = []
    for line in command.get("output", "").splitlines():
        lowered = line.lower()
        if any(keyword in lowered for keyword in keywords):
            matches.append(line)
    filtered = dict(command)
    filtered["raw_line_count"] = len(command.get("output", "").splitlines())
    filtered["matched_line_count"] = len(matches)
    filtered["output"] = "\n".join(matches[-120:])[:MAX_OUTPUT_CHARS] or "No matching Pop!_OS/COSMIC UI lines found."
    return filtered


def collect_cosmic_process_state() -> list[dict]:
    return _run_available([["pgrep", "-a", "cosmic"]])


def collect_user_service_state() -> dict:
    commands = _run_available(
        [
            ["systemctl", "--user", "--failed", "--no-legend", "--plain"],
            ["systemctl", "--user", "list-units", "--type=service", "--state=running", "--no-pager"],
        ]
    )
    failed = []
    if commands:
        failed = [line for line in commands[0].get("output", "").splitlines() if line.strip()]
    return {"commands": commands, "failed_services": failed[:30], "failed_count": len(failed)}


def collect_display_state() -> dict:
    commands = _run_available(
        [
            ["cosmic-randr", "list"],
            ["xrandr", "--query"],
            ["wayland-info"],
            ["lsusb"],
            ["lspci", "-nnk"],
        ]
    )
    return {"commands": commands}


def collect_gpu_state() -> dict:
    commands = _run_available([["lspci", "-nnk"], ["mokutil", "--sb-state"]])
    return {"commands": commands}


def collect_update_state() -> dict:
    commands = _run_available(
        [
            ["apt-get", "check"],
            ["apt", "list", "--upgradable"],
            ["apt-mark", "showhold"],
            ["dpkg-query", "-W", "pop-*", "cosmic-*", "system76-*"],
            ["apt-cache", "policy", "pop-desktop", "cosmic-session", "cosmic-comp", "cosmic-settings", "cosmic-store"],
            ["flatpak", "list", "--app"],
            ["flatpak", "remotes"],
            ["flatpak", "remote-ls", "--updates"],
            ["fwupdmgr", "get-updates"],
            ["system76-firmware-cli", "info"],
            ["pop-upgrade", "status"],
        ],
        timeout=UPDATE_TIMEOUT,
    )
    apt_health = None
    upgradable_count = None
    for command in commands:
        if command["command"].startswith("apt-get check"):
            apt_health = command["exit_code"] == 0
        if command["command"].startswith("apt list --upgradable"):
            upgradable_count = len(
                [
                    line
                    for line in command["output"].splitlines()
                    if "/" in line and not line.lower().startswith("listing")
                ]
            )
    return {"commands": commands, "apt_health_ok": apt_health, "upgradable_count": upgradable_count}


def collect_cosmic_config_inventory() -> dict:
    roots = [
        Path.home() / ".config" / "cosmic",
        Path.home() / ".config" / "pop-shell",
        Path.home() / ".local" / "share" / "cosmic",
        Path.home() / ".config" / "autostart",
    ]
    entries: list[dict[str, Any]] = []
    for root in roots:
        if not root.exists():
            entries.append({"path": sanitize_output(str(root)), "exists": False})
            continue
        for item in list(root.rglob("*"))[:160]:
            try:
                stat = item.stat()
            except OSError:
                continue
            entries.append(
                {
                    "path": sanitize_output(str(item)),
                    "exists": True,
                    "is_dir": item.is_dir(),
                    "size": stat.st_size,
                    "modified_at": dt.datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
                }
            )
    return {"entries": entries}


def collect_recent_ui_logs() -> dict:
    commands = []
    if shutil.which("journalctl"):
        commands.append(_filter_log_command(_run_read_only(["journalctl", "--user", "-b", "--no-pager", "-n", "500"])))
        commands.append(_filter_log_command(_run_read_only(["journalctl", "-b", "--no-pager", "-n", "500"])))
    return {"commands": commands}


def collect_power_suspend_state() -> dict:
    commands = _run_available(
        [
            ["journalctl", "-b", "--no-pager", "-n", "300"],
            ["systemctl", "status", "systemd-suspend.service", "--no-pager"],
        ]
    )
    filtered = [_filter_log_command(command, ("suspend", "resume", "sleep", "wake", "cosmic", "display", "drm", "error")) for command in commands]
    return {"commands": filtered}


def run_pop_cosmic_deep_scan(scope: str = "standard") -> dict:
    selected_scope = scope if scope in SCAN_SCOPES else "standard"
    profile = detect_pop_cosmic_environment()
    groups: dict[str, Any] = {
        "profile": profile,
        "processes": {"commands": collect_cosmic_process_state()},
        "user_services": collect_user_service_state(),
        "logs": collect_recent_ui_logs(),
    }
    if selected_scope in {"standard", "display", "full"}:
        groups["display"] = collect_display_state()
        groups["gpu"] = collect_gpu_state()
    if selected_scope in {"standard", "updates", "full"}:
        groups["updates"] = collect_update_state()
    if selected_scope == "full":
        groups["config_inventory"] = collect_cosmic_config_inventory()
        groups["power_suspend"] = collect_power_suspend_state()

    findings = summarize_scan_findings(groups)
    return {
        "generated_at": _now(),
        "scope": selected_scope,
        "applicable": profile.get("applicable", False),
        "profile": profile,
        "groups": groups,
        "findings": findings,
        "privacy": {
            "redacted_user_paths": True,
            "redacted_hostnames": True,
            "redacted_tokens": True,
            "output_cap_chars": MAX_OUTPUT_CHARS,
        },
    }


def summarize_scan_findings(groups: dict[str, Any]) -> list[dict]:
    findings = []
    profile = groups.get("profile", {})
    if not profile.get("applicable"):
        findings.append(
            {
                "id": "pop-cosmic-not-detected",
                "severity": "info",
                "summary": "No Pop!_OS or COSMIC signal was detected in the current session.",
            }
        )
    elif profile.get("is_pop_os"):
        findings.append(
            {
                "id": "pop-os-detected",
                "severity": "info",
                "summary": f"{profile.get('pretty_name')} detected with COSMIC signal={profile.get('has_cosmic_signal')}.",
            }
        )
    user_services = groups.get("user_services", {})
    if user_services.get("failed_count"):
        findings.append(
            {
                "id": "pop-cosmic-user-service-failures",
                "severity": "warning",
                "summary": f"{user_services['failed_count']} failed user service line(s) were detected.",
            }
        )
    updates = groups.get("updates", {})
    if updates.get("apt_health_ok") is False:
        findings.append(
            {
                "id": "pop-cosmic-apt-health",
                "severity": "warning",
                "summary": "APT health check reported a problem; do not upgrade before repair planning.",
            }
        )
    if updates.get("upgradable_count"):
        findings.append(
            {
                "id": "pop-cosmic-updates-available",
                "severity": "info",
                "summary": f"{updates['upgradable_count']} package update(s) are visible from the current package index.",
            }
        )
    return findings
