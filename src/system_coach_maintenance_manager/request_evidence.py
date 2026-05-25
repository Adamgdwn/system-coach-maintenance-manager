"""Read-only evidence collection for Request Desk reasoning."""

from __future__ import annotations

import datetime as dt
import platform
import re
import shutil
import subprocess
import time
from pathlib import Path


REQUEST_EVIDENCE_TIMEOUT = 5
MAX_OUTPUT_CHARS = 5000
COSMIC_SHELL_TERMS = (
    "panel icon",
    "panel icons",
    "bottom bar",
    "top bar",
    "left side of the bottom bar",
    "right side of the bottom bar",
    "system tray",
    "tray icon",
    "tray icons",
    "applet",
    "applets",
    "launcher icon",
    "launcher icons",
)


def _now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _has_any(text: str, words: tuple[str, ...]) -> bool:
    for word in words:
        if re.fullmatch(r"[a-z0-9]+", word):
            if re.search(rf"\b{re.escape(word)}\b", text):
                return True
        elif word in text:
            return True
    return False


def _run_read_only(args: list[str], timeout: int = REQUEST_EVIDENCE_TIMEOUT) -> dict:
    started = time.time()
    try:
        completed = subprocess.run(
            args,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = (completed.stdout or completed.stderr or "").strip()
        return {
            "command": " ".join(args),
            "exit_code": completed.returncode,
            "output": output[:MAX_OUTPUT_CHARS],
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
            "output": "Timed out while collecting this read-only request evidence.",
            "duration_ms": int((time.time() - started) * 1000),
        }


def _linux_desktop_context() -> dict:
    import os

    return {
        "current_desktop": os.environ.get("XDG_CURRENT_DESKTOP", "unknown"),
        "desktop_session": os.environ.get("DESKTOP_SESSION", "unknown"),
        "session_type": os.environ.get("XDG_SESSION_TYPE", "unknown"),
        "display": os.environ.get("DISPLAY", "unknown"),
        "wayland_display": os.environ.get("WAYLAND_DISPLAY", "unknown"),
    }


def _request_scopes(normalized: str, desktop_hint: str | None = None) -> list[str]:
    scopes = []
    hint = _normalize(desktop_hint or "")
    scope_keywords = {
        "display-dock": (
            "display",
            "monitor",
            "screen",
            "dock",
            "docking",
            "dell",
            "displaylink",
            "cursor",
            "pointer",
            "jitter",
            "jittery",
            "rotated",
            "rotation",
            "scale",
            "scaling",
            "refresh",
            "hz",
            "hidden",
            "bottom half",
        ),
        "audio-routing": ("audio", "sound", "speaker", "speakers", "microphone", "mic", "volume", "input", "output"),
        "network-dns": ("network", "dns", "wifi", "wi-fi", "internet", "route", "gateway", "resolver", "connection"),
        "package-updates": ("package", "update", "upgrade", "apt", "dnf", "pacman", "winget", "choco"),
        "docker-cleanup": ("docker", "container", "containers", "image", "images", "volume", "volumes", "prune"),
        "startup-apps": ("startup", "start up", "login item", "autostart", "boot app", "launch at login"),
        "slow-computer": ("slow", "sluggish", "lag", "laggy", "performance", "freezing", "hang", "memory", "cpu", "disk"),
        "services-logs": ("service", "services", "failed", "error", "errors", "log", "logs", "crash", "crashes"),
        "pop-cosmic": (
            "pop os",
            "pop!_os",
            "pop! os",
            "popos",
            "cosmic",
            "cosmic store",
            "cosmic panel",
            "cosmic launcher",
            "cosmic settings",
            "wayland",
            "xwayland",
            "compositor",
            "workspace",
        ),
    }
    for scope, keywords in scope_keywords.items():
        if _has_any(normalized, keywords):
            scopes.append(scope)
    if "pop-cosmic" not in scopes and "cosmic" in hint and _has_any(normalized, COSMIC_SHELL_TERMS):
        scopes.append("pop-cosmic")
    return scopes or ["system-basics"]


def _filter_log_output(command: dict, keywords: tuple[str, ...]) -> dict:
    lines = []
    for line in command.get("output", "").splitlines():
        lowered = line.lower()
        if any(keyword in lowered for keyword in keywords):
            lines.append(line)
    filtered = dict(command)
    filtered["output"] = "\n".join(lines[-80:])[:MAX_OUTPUT_CHARS] or "No matching lines found in recent logs."
    return filtered


def _linux_display_evidence(desktop_hint: str | None) -> list[dict]:
    commands: list[list[str]] = []
    hint = _normalize(desktop_hint or "")
    if shutil.which("cosmic-randr") and ("cosmic" in hint or not hint):
        commands.append(["cosmic-randr", "list"])
    if shutil.which("xrandr"):
        commands.append(["xrandr", "--query"])
    if shutil.which("lsusb"):
        commands.append(["lsusb"])
    if shutil.which("lspci"):
        commands.append(["lspci"])
    if shutil.which("journalctl"):
        commands.append(["journalctl", "-b", "-n", "500", "--no-pager"])

    results = []
    for args in commands:
        result = _run_read_only(args)
        if args[0] == "journalctl":
            result = _filter_log_output(
                result,
                (
                    "cosmic",
                    "display",
                    "monitor",
                    "connector",
                    "hotplug",
                    "dock",
                    "dell",
                    "displaylink",
                    "cursor",
                    "pointer",
                    "wayland",
                    "egl",
                    "gl_invalid",
                    "drm",
                    "panel",
                ),
            )
        results.append(result)
    return results


def _linux_audio_evidence() -> list[dict]:
    commands = []
    if shutil.which("pactl"):
        commands.extend([["pactl", "info"], ["pactl", "list", "short", "sinks"], ["pactl", "list", "short", "sources"]])
    return [_run_read_only(args) for args in commands]


def _linux_network_evidence() -> list[dict]:
    commands = []
    if shutil.which("ip"):
        commands.append(["ip", "route"])
    if shutil.which("resolvectl"):
        commands.append(["resolvectl", "status"])
    if shutil.which("nmcli"):
        commands.append(["nmcli", "device", "status"])
    return [_run_read_only(args) for args in commands]


def _linux_package_evidence() -> list[dict]:
    commands = []
    for args in (["apt-get", "check"], ["dnf", "check"], ["pacman", "-Dk"]):
        if shutil.which(args[0]):
            commands.append(args)
    return [_run_read_only(args) for args in commands]


def _linux_docker_evidence() -> list[dict]:
    if not shutil.which("docker"):
        return []
    return [
        _run_read_only(["docker", "system", "df"]),
        _run_read_only(["docker", "ps", "-a"]),
        _run_read_only(["docker", "images"]),
        _run_read_only(["docker", "volume", "ls"]),
    ]


def _linux_startup_evidence() -> list[dict]:
    commands = []
    if shutil.which("systemctl"):
        commands.append(["systemctl", "--user", "list-unit-files", "--state=enabled"])
    autostart = Path.home() / ".config" / "autostart"
    if autostart.exists():
        commands.append(["ls", str(autostart)])
    if shutil.which("crontab"):
        commands.append(["crontab", "-l"])
    return [_run_read_only(args) for args in commands]


def _linux_performance_evidence() -> list[dict]:
    commands = []
    for args in (
        ["uptime"],
        ["free", "-h"],
        ["df", "-h"],
        ["ps", "-eo", "pid,comm,%cpu,%mem", "--sort=-%cpu"],
    ):
        if shutil.which(args[0]):
            commands.append(args)
    return [_run_read_only(args) for args in commands]


def _linux_services_logs_evidence() -> list[dict]:
    results = []
    if shutil.which("systemctl"):
        results.append(_run_read_only(["systemctl", "--failed", "--no-legend", "--plain"]))
    if shutil.which("journalctl"):
        result = _run_read_only(["journalctl", "-p", "3", "-n", "100", "--no-pager"])
        results.append(
            _filter_log_output(
                result,
                ("error", "failed", "critical", "crash", "exception", "traceback", "segfault", "timeout"),
            )
        )
    return results


def _linux_pop_cosmic_evidence() -> list[dict]:
    commands = []
    if Path("/etc/os-release").exists():
        commands.append(["cat", "/etc/os-release"])
    for args in (
        ["pgrep", "-a", "cosmic"],
        ["systemctl", "--user", "--failed", "--no-legend", "--plain"],
        ["journalctl", "--user", "-b", "-n", "300", "--no-pager"],
        ["cosmic-randr", "list"],
        ["apt-get", "check"],
        ["apt", "list", "--upgradable"],
    ):
        if shutil.which(args[0]):
            commands.append(args)
    results = []
    for args in commands:
        result = _run_read_only(args)
        if args[0] == "journalctl":
            result = _filter_log_output(
                result,
                (
                    "cosmic",
                    "cosmic-comp",
                    "cosmic-panel",
                    "wayland",
                    "xwayland",
                    "compositor",
                    "display",
                    "monitor",
                    "cursor",
                    "dock",
                    "failed",
                    "error",
                    "crash",
                    "timeout",
                ),
            )
        results.append(result)
    return results


def _linux_system_basics() -> list[dict]:
    commands = []
    for args in (["uname", "-a"], ["uptime"], ["df", "-h"]):
        if shutil.which(args[0]):
            commands.append(args)
    return [_run_read_only(args) for args in commands]


def _windows_display_evidence() -> list[dict]:
    if not shutil.which("powershell") and not shutil.which("pwsh"):
        return []
    shell = "powershell" if shutil.which("powershell") else "pwsh"
    commands = [
        [shell, "-NoProfile", "-Command", "Get-CimInstance Win32_DesktopMonitor"],
        [shell, "-NoProfile", "-Command", "Get-CimInstance Win32_VideoController"],
        [
            shell,
            "-NoProfile",
            "-Command",
            "Get-PnpDevice | Where-Object {$_.FriendlyName -match 'Display|Dock|USB|Monitor'}",
        ],
    ]
    return [_run_read_only(args) for args in commands]


def _windows_shell() -> str | None:
    if shutil.which("powershell"):
        return "powershell"
    if shutil.which("pwsh"):
        return "pwsh"
    return None


def _windows_evidence(scopes: list[str]) -> list[dict]:
    shell = _windows_shell()
    if not shell:
        return []
    command_map = {
        "audio-routing": [[shell, "-NoProfile", "-Command", "Get-CimInstance Win32_SoundDevice"]],
        "network-dns": [
            ["ipconfig", "/all"],
            ["route", "print"],
            [shell, "-NoProfile", "-Command", "Get-DnsClientServerAddress"],
        ],
        "package-updates": [[shell, "-NoProfile", "-Command", "winget --info"]],
        "docker-cleanup": [
            ["docker", "system", "df"],
            ["docker", "ps", "-a"],
            ["docker", "images"],
            ["docker", "volume", "ls"],
        ],
        "startup-apps": [
            [shell, "-NoProfile", "-Command", "Get-CimInstance Win32_StartupCommand | Select-Object Name,Command,Location"]
        ],
        "slow-computer": [
            [shell, "-NoProfile", "-Command", "Get-Process | Sort-Object CPU -Descending | Select-Object -First 20 Name,CPU,WorkingSet"],
            [shell, "-NoProfile", "-Command", "Get-CimInstance Win32_OperatingSystem | Select-Object FreePhysicalMemory,TotalVisibleMemorySize"],
        ],
        "services-logs": [
            [shell, "-NoProfile", "-Command", "Get-CimInstance Win32_Service | Where-Object {$_.State -ne 'Running'} | Select-Object -First 30 Name,State,StartMode"],
            ["wevtutil", "qe", "System", "/c:50", "/f:text"],
        ],
        "system-basics": [
            [shell, "-NoProfile", "-Command", "Get-CimInstance Win32_OperatingSystem"],
            [shell, "-NoProfile", "-Command", "Get-PSDrive -PSProvider FileSystem"],
        ],
    }
    commands = []
    for scope in scopes:
        commands.extend(command_map.get(scope, []))
    return [_run_read_only(args) for args in commands if shutil.which(args[0])]


def _linux_evidence(scopes: list[str], desktop_hint: str | None) -> list[dict]:
    collectors = {
        "display-dock": lambda: _linux_display_evidence(desktop_hint),
        "audio-routing": _linux_audio_evidence,
        "network-dns": _linux_network_evidence,
        "package-updates": _linux_package_evidence,
        "docker-cleanup": _linux_docker_evidence,
        "startup-apps": _linux_startup_evidence,
        "slow-computer": _linux_performance_evidence,
        "services-logs": _linux_services_logs_evidence,
        "pop-cosmic": _linux_pop_cosmic_evidence,
        "system-basics": _linux_system_basics,
    }
    results = []
    for scope in scopes:
        collector = collectors.get(scope)
        if collector:
            results.extend(collector())
    return results


def collect_request_evidence(
    request_text: str,
    *,
    os_name: str | None = None,
    desktop_hint: str | None = None,
) -> dict:
    """Collect bounded read-only facts before the model reasons about a request."""

    resolved_os = os_name or platform.system() or "Unknown"
    normalized = _normalize(request_text)
    evidence = {
        "generated_at": _now(),
        "os": resolved_os,
        "desktop_hint": desktop_hint,
        "scopes": [],
        "facts": {},
        "commands": [],
    }
    scopes = _request_scopes(normalized, desktop_hint)
    evidence["scopes"] = scopes

    if resolved_os.lower() == "linux":
        evidence["facts"]["desktop"] = _linux_desktop_context()
        evidence["commands"] = _linux_evidence(scopes, desktop_hint)
    elif resolved_os.lower().startswith("win"):
        display_commands = _windows_display_evidence() if "display-dock" in scopes else []
        evidence["commands"] = display_commands + _windows_evidence([scope for scope in scopes if scope != "display-dock"])

    return evidence
