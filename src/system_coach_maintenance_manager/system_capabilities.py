"""Portable local capability discovery for first-run public installs."""

from __future__ import annotations

import datetime as dt
import json
import os
import platform
from pathlib import Path
import shutil
import subprocess
import time
import urllib.error
import urllib.request

from .ai_engine import OLLAMA_URL, choose_request_brain_models
from .maintenance_history import history_dir
from .model_providers import model_provider_status
from .pop_cosmic_profile import is_pop_os, read_os_release


COMMAND_TIMEOUT = 4
MAX_SUMMARY_CHARS = 1800

PACKAGE_MANAGERS = (
    "apt",
    "apt-get",
    "dnf",
    "pacman",
    "zypper",
    "flatpak",
    "snap",
    "winget",
    "choco",
)
MAINTENANCE_COMMANDS = (
    "systemctl",
    "journalctl",
    "findmnt",
    "free",
    "df",
    "ip",
    "resolvectl",
    "docker",
    "podman",
    "cosmic-randr",
    "cosmic-settings",
    "xrandr",
    "wayland-info",
    "lspci",
    "lsusb",
    "fwupdmgr",
    "system76-firmware-cli",
    "pop-upgrade",
    "powershell",
    "pwsh",
    "wevtutil",
)
PRIVILEGE_HELPERS = ("pkexec", "sudo", "doas", "runas", "powershell")
MODEL_RUNTIMES = ("ollama", "llama-server", "lmstudio")


def _now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def _available(command: str) -> dict:
    path = shutil.which(command)
    return {"present": bool(path), "path": path}


def _command_inventory(commands: tuple[str, ...]) -> dict:
    return {command: _available(command) for command in commands}


def _run_read_only(args: list[str], timeout: int = COMMAND_TIMEOUT) -> dict:
    started = time.time()
    try:
        completed = subprocess.run(args, check=False, capture_output=True, text=True, timeout=timeout)
        output = (completed.stdout or completed.stderr or "").strip()
        return {
            "command": " ".join(args),
            "exit_code": completed.returncode,
            "output": output[:MAX_SUMMARY_CHARS],
            "duration_ms": int((time.time() - started) * 1000),
        }
    except (FileNotFoundError, PermissionError) as exc:
        return {
            "command": " ".join(args),
            "exit_code": 127,
            "output": str(exc) or "Command is not available on this machine.",
            "duration_ms": int((time.time() - started) * 1000),
        }
    except subprocess.TimeoutExpired:
        return {
            "command": " ".join(args),
            "exit_code": 124,
            "output": "Timed out while collecting bounded capability evidence.",
            "duration_ms": int((time.time() - started) * 1000),
        }


def _distribution(os_name: str) -> dict:
    if os_name.lower() != "linux":
        return {"id": os_name.lower() or "unknown", "id_like": [], "version": platform.version(), "pretty_name": platform.platform()}
    values = read_os_release()
    return {
        "id": values.get("ID", "unknown").lower(),
        "id_like": [item.strip().lower() for item in values.get("ID_LIKE", "").split() if item.strip()],
        "version": values.get("VERSION_ID", "unknown"),
        "pretty_name": values.get("PRETTY_NAME") or values.get("NAME") or "Unknown Linux",
    }


def _desktop_profile(os_name: str, commands: dict) -> dict:
    if os_name.lower() == "linux":
        desktop_blob = " ".join(
            [
                os.environ.get("XDG_CURRENT_DESKTOP", ""),
                os.environ.get("XDG_SESSION_DESKTOP", ""),
                os.environ.get("DESKTOP_SESSION", ""),
            ]
        ).lower()
        if "cosmic" in desktop_blob or commands.get("cosmic-settings", {}).get("present"):
            family = "cosmic"
        elif "gnome" in desktop_blob:
            family = "gnome"
        elif "kde" in desktop_blob or "plasma" in desktop_blob:
            family = "kde"
        elif "xfce" in desktop_blob:
            family = "xfce"
        else:
            family = "unknown-linux-desktop"
        return {
            "family": family,
            "current_desktop": os.environ.get("XDG_CURRENT_DESKTOP", "unknown"),
            "session_desktop": os.environ.get("XDG_SESSION_DESKTOP", "unknown"),
            "desktop_session": os.environ.get("DESKTOP_SESSION", "unknown"),
            "session_type": os.environ.get("XDG_SESSION_TYPE", "unknown"),
            "display": "wayland" if os.environ.get("WAYLAND_DISPLAY") else "x11" if os.environ.get("DISPLAY") else "unknown",
        }
    if os_name.lower().startswith("win"):
        return {
            "family": "windows-shell",
            "current_desktop": "Windows Shell",
            "session_desktop": os.environ.get("SESSIONNAME", "unknown"),
            "desktop_session": os.environ.get("SESSIONNAME", "unknown"),
            "session_type": "windows",
            "display": "windows",
        }
    return {
        "family": "unknown",
        "current_desktop": "unknown",
        "session_desktop": "unknown",
        "desktop_session": "unknown",
        "session_type": "unknown",
        "display": "unknown",
    }


def _hardware_profile(os_name: str, commands: dict) -> dict:
    gpu_summary = "GPU detection command is not available."
    gpu_command = None
    if os_name.lower() == "linux" and commands.get("lspci", {}).get("present"):
        gpu_command = _run_read_only(["lspci", "-nn"])
        lines = [
            line
            for line in gpu_command.get("output", "").splitlines()
            if any(token in line.lower() for token in ("vga", "3d controller", "display controller", "nvidia", "amd", "intel"))
        ]
        gpu_summary = "\n".join(lines[:12]) or "No GPU/display controller lines found in lspci output."
    return {
        "architecture": platform.machine() or "unknown",
        "processor": platform.processor() or "unknown",
        "hardware_class": "windows-pc" if os_name.lower().startswith("win") else "linux-pc" if os_name.lower() == "linux" else "unknown",
        "gpu": {
            "available": gpu_command is not None and gpu_command.get("exit_code") == 0,
            "summary": gpu_summary,
            "commands": [gpu_command] if gpu_command else [],
        },
    }


def _ollama_status() -> dict:
    present = bool(shutil.which("ollama"))
    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=0.75) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError, TimeoutError) as exc:
        return {
            "present": present,
            "api_available": False,
            "models": [],
            "request_brain_models": [],
            "message": f"Ollama command {'is' if present else 'is not'} installed; local API is not reachable: {exc}",
        }
    models = [item.get("name", "") for item in data.get("models", []) if item.get("name")]
    return {
        "present": present,
        "api_available": True,
        "models": models,
        "request_brain_models": choose_request_brain_models(models),
        "message": "Ollama local API is reachable." if models else "Ollama is reachable, but no local models are installed.",
    }


def _model_runtimes() -> dict:
    runtimes = _command_inventory(MODEL_RUNTIMES)
    runtimes["ollama"].update(_ollama_status())
    return runtimes


def _display_stack(desktop: dict, commands: dict) -> dict:
    return {
        "display_server": desktop.get("display", "unknown"),
        "wayland_available": bool(os.environ.get("WAYLAND_DISPLAY")) or commands.get("wayland-info", {}).get("present", False),
        "x11_available": bool(os.environ.get("DISPLAY")) or commands.get("xrandr", {}).get("present", False),
        "cosmic_tools_available": commands.get("cosmic-settings", {}).get("present", False)
        or commands.get("cosmic-randr", {}).get("present", False),
        "display_commands": {
            command: commands.get(command, {"present": False, "path": None})
            for command in ("cosmic-randr", "cosmic-settings", "xrandr", "wayland-info")
        },
    }


def _docs_for(os_name: str, distribution: dict, desktop: dict) -> list[str]:
    docs = ["README.md", "docs/manual.md", "docs/release-checklist.md"]
    distro_id = distribution.get("id", "")
    id_like = set(distribution.get("id_like", []))
    if os_name.lower() == "linux":
        docs.append("docs/setup-linux.md")
        if distro_id in {"pop", "ubuntu", "debian"} or {"ubuntu", "debian"} & id_like:
            docs.append("docs/setup-linux.md#ubuntu-and-debian")
        elif distro_id == "fedora" or "fedora" in id_like:
            docs.append("docs/setup-linux.md#fedora")
        elif distro_id == "arch" or "arch" in id_like:
            docs.append("docs/setup-linux.md#arch-linux")
        if desktop.get("family") == "cosmic" or distro_id == "pop":
            docs.append("docs/pop-cosmic-agent.md")
    elif os_name.lower().startswith("win"):
        docs.append("docs/setup-windows-browser.md")
    return docs


def _surface_matrix(os_name: str, distribution: dict, desktop: dict, commands: dict, models: dict, provider_status: dict) -> list[dict]:
    is_linux = os_name.lower() == "linux"
    is_windows = os_name.lower().startswith("win")
    pop_or_cosmic = is_linux and (distribution.get("id") == "pop" or desktop.get("family") == "cosmic")
    ollama = models.get("ollama", {})
    return [
        {
            "id": "local-review",
            "label": "Local Review",
            "available": True,
            "reason": "Portable read-only environment review is available on this machine.",
        },
        {
            "id": "maintenance-diagnostics",
            "label": "Maintenance Diagnostics",
            "available": is_linux or is_windows,
            "reason": "Read-only diagnostics support Linux and Windows browser mode." if (is_linux or is_windows) else "This OS is not in the built-in diagnostics catalog yet.",
        },
        {
            "id": "request-desk",
            "label": "Request Desk",
            "available": True,
            "reason": "Request planning can fall back to deterministic triage when platform-specific commands are unavailable.",
        },
        {
            "id": "pop-cosmic-agent",
            "label": "Pop!_OS + COSMIC Agent",
            "available": pop_or_cosmic,
            "reason": "Pop/COSMIC signal detected." if pop_or_cosmic else "Hidden or advisory unless Pop!_OS or COSMIC signals are detected.",
        },
        {
            "id": "local-model-coach",
            "label": "Local Model Coach",
            "available": bool(ollama.get("api_available") and ollama.get("request_brain_models")),
            "reason": ollama.get("message", "No local model runtime detected."),
        },
        {
            "id": "model-provider-setup",
            "label": "Model Provider Setup",
            "available": True,
            "reason": f"Effective mode: {provider_status.get('effective_mode', 'deterministic')}. {provider_status.get('privacy', '')}",
        },
        {
            "id": "elevated-runner",
            "label": "Elevated Action Runner",
            "available": bool(commands.get("pkexec", {}).get("present") or is_windows),
            "reason": "Privilege helper detected; every elevated action still requires approval." if (commands.get("pkexec", {}).get("present") or is_windows) else "No supported privilege helper was detected.",
        },
    ]


def _scan_scope_matrix(os_name: str, distribution: dict, desktop: dict, commands: dict) -> list[dict]:
    is_linux = os_name.lower() == "linux"
    pop_or_cosmic = is_linux and (distribution.get("id") == "pop" or desktop.get("family") == "cosmic")
    return [
        {"id": "filesystem-map", "available": True, "reason": "Available after the user selects roots to inspect."},
        {"id": "maintenance-standard", "available": is_linux or os_name.lower().startswith("win"), "reason": "Read-only OS health checks."},
        {"id": "pop-cosmic-standard", "available": pop_or_cosmic, "reason": "Requires Pop!_OS or COSMIC session signal."},
        {
            "id": "display",
            "available": bool(commands.get("cosmic-randr", {}).get("present") or commands.get("xrandr", {}).get("present") or os_name.lower().startswith("win")),
            "reason": "Display commands detected." if is_linux else "Windows display checks route through Settings/manual review.",
        },
        {
            "id": "updates",
            "available": any(commands.get(command, {}).get("present") for command in ("apt", "apt-get", "dnf", "pacman", "winget", "choco")),
            "reason": "Package manager detected.",
        },
    ]


def _local_storage_policy() -> dict:
    config_dir = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "system-coach-maintenance-manager"
    return {
        "history_dir": str(history_dir()),
        "machine_profile_path": str(config_dir / "machine-profile.json"),
        "repository_storage_allowed": False,
        "summary": "Machine-specific preferences and lessons are stored in local user/history paths, not committed to the repository.",
    }


def detect_system_capabilities() -> dict:
    os_name = platform.system() or "Unknown"
    distribution = _distribution(os_name)
    command_names = tuple(sorted(set(PACKAGE_MANAGERS + MAINTENANCE_COMMANDS + PRIVILEGE_HELPERS)))
    commands = _command_inventory(command_names)
    desktop = _desktop_profile(os_name, commands)
    models = _model_runtimes()
    provider_status = model_provider_status()
    return {
        "generated_at": _now(),
        "onboarding_mode": "unknown-machine-first-run",
        "privacy": "Capability discovery uses bounded local checks and stores machine-specific state outside the repository.",
        "os": {
            "system": os_name,
            "release": platform.release(),
            "platform": platform.platform(),
            "distribution": distribution,
            "is_pop_os": is_pop_os({"ID": distribution.get("id", ""), "ID_LIKE": " ".join(distribution.get("id_like", [])), "NAME": distribution.get("pretty_name", "")})
            if os_name.lower() == "linux"
            else False,
        },
        "desktop": desktop,
        "package_managers": {command: commands[command] for command in PACKAGE_MANAGERS},
        "privilege_helpers": {command: commands.get(command, {"present": False, "path": None}) for command in PRIVILEGE_HELPERS},
        "maintenance_commands": {command: commands.get(command, {"present": False, "path": None}) for command in MAINTENANCE_COMMANDS},
        "hardware": _hardware_profile(os_name, commands),
        "display_stack": _display_stack(desktop, commands),
        "model_runtimes": models,
        "model_provider_status": provider_status,
        "surfaces": _surface_matrix(os_name, distribution, desktop, commands, models, provider_status),
        "scan_scopes": _scan_scope_matrix(os_name, distribution, desktop, commands),
        "recommended_docs": _docs_for(os_name, distribution, desktop),
        "local_storage": _local_storage_policy(),
    }
