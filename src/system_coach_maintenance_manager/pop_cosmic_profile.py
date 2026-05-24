"""Pop!_OS and COSMIC environment profile detection."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import time


PROFILE_TIMEOUT = 5
MAX_OUTPUT_CHARS = 3000
COSMIC_COMMANDS = (
    "cosmic-session",
    "cosmic-comp",
    "cosmic-panel",
    "cosmic-randr",
    "cosmic-settings",
    "cosmic-store",
)
SUPPORT_COMMANDS = (
    "apt",
    "apt-get",
    "apt-cache",
    "apt-mark",
    "dpkg-query",
    "flatpak",
    "fwupdmgr",
    "hostnamectl",
    "loginctl",
    "lspci",
    "lsusb",
    "mokutil",
    "pop-upgrade",
    "system76-firmware-cli",
    "systemctl",
    "uname",
)


def _run_read_only(args: list[str], timeout: int = PROFILE_TIMEOUT) -> dict:
    started = time.time()
    try:
        completed = subprocess.run(args, check=False, capture_output=True, text=True, timeout=timeout)
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
            "output": "Timed out while collecting profile evidence.",
            "duration_ms": int((time.time() - started) * 1000),
        }


def read_os_release(path: Path = Path("/etc/os-release")) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return values
    for line in lines:
        if "=" not in line or line.strip().startswith("#"):
            continue
        key, raw_value = line.split("=", 1)
        values[key] = raw_value.strip().strip('"')
    return values


def is_pop_os(os_release: dict[str, str]) -> bool:
    ids = {
        os_release.get("ID", "").lower(),
        *[item.strip().lower() for item in os_release.get("ID_LIKE", "").split()],
    }
    return "pop" in ids or "pop_os" in ids or "pop!_os" in os_release.get("NAME", "").lower()


def detect_session() -> dict:
    session = {
        "current_desktop": os.environ.get("XDG_CURRENT_DESKTOP", "unknown"),
        "session_desktop": os.environ.get("XDG_SESSION_DESKTOP", "unknown"),
        "desktop_session": os.environ.get("DESKTOP_SESSION", "unknown"),
        "session_type": os.environ.get("XDG_SESSION_TYPE", "unknown"),
        "display": os.environ.get("DISPLAY", "unknown"),
        "wayland_display": os.environ.get("WAYLAND_DISPLAY", "unknown"),
    }
    session_id = os.environ.get("XDG_SESSION_ID")
    if session_id and shutil.which("loginctl"):
        session["loginctl"] = _run_read_only(["loginctl", "show-session", session_id, "--no-pager"])["output"]
    return session


def detect_cosmic_components() -> dict:
    commands = {command: shutil.which(command) for command in COSMIC_COMMANDS}
    present = [command for command, path in commands.items() if path]
    return {
        "commands": {command: {"present": bool(path), "path": path} for command, path in commands.items()},
        "present": present,
        "has_cosmic_tools": bool(present),
    }


def detect_system76_hardware() -> dict:
    evidence = []
    if shutil.which("hostnamectl"):
        evidence.append(_run_read_only(["hostnamectl"]))
    if shutil.which("system76-firmware-cli"):
        evidence.append(_run_read_only(["system76-firmware-cli", "info"]))
    blob = "\n".join(item.get("output", "") for item in evidence).lower()
    return {
        "detected": "system76" in blob,
        "commands": evidence,
    }


def _gpu_summary() -> dict:
    if not shutil.which("lspci"):
        return {"available": False, "summary": "lspci is not available.", "commands": []}
    command = _run_read_only(["lspci", "-nnk"])
    lines = [
        line
        for line in command.get("output", "").splitlines()
        if any(token in line.lower() for token in ("vga", "3d controller", "display controller", "nvidia", "amd", "intel"))
    ]
    return {"available": command["exit_code"] == 0, "summary": "\n".join(lines[:20]), "commands": [command]}


def _secure_boot_summary() -> dict:
    if not shutil.which("mokutil"):
        return {"available": False, "summary": "mokutil is not available.", "commands": []}
    command = _run_read_only(["mokutil", "--sb-state"])
    return {"available": command["exit_code"] == 0, "summary": command.get("output", ""), "commands": [command]}


def detect_pop_cosmic_environment() -> dict:
    os_release = read_os_release()
    session = detect_session()
    cosmic = detect_cosmic_components()
    desktop_blob = " ".join(str(value).lower() for value in session.values())
    has_cosmic_session = "cosmic" in desktop_blob or cosmic["has_cosmic_tools"]
    support_commands = {command: shutil.which(command) for command in SUPPORT_COMMANDS}
    return {
        "os_release": os_release,
        "is_pop_os": is_pop_os(os_release),
        "pop_version": os_release.get("VERSION_ID", "unknown"),
        "pretty_name": os_release.get("PRETTY_NAME") or os_release.get("NAME") or "Unknown Linux",
        "session": session,
        "cosmic": cosmic,
        "has_cosmic_signal": has_cosmic_session,
        "applicable": is_pop_os(os_release) or has_cosmic_session,
        "system76_hardware": detect_system76_hardware(),
        "gpu": _gpu_summary(),
        "secure_boot": _secure_boot_summary(),
        "support_commands": {
            command: {"present": bool(path), "path": path} for command, path in support_commands.items()
        },
    }
