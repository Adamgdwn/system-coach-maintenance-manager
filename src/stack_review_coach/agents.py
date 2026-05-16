"""Local probe agents that inspect the machine by running shell commands."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import platform
import re
import shlex
import shutil
import subprocess
import time


def _run_command(command: str, timeout: int = 8) -> dict:
    started = time.time()
    try:
        completed = subprocess.run(
            command,
            shell=True,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = (completed.stdout or completed.stderr).strip()
        return {
            "command": command,
            "exit_code": completed.returncode,
            "output": output[:1200],
            "duration_ms": int((time.time() - started) * 1000),
        }
    except subprocess.TimeoutExpired:
        return {
            "command": command,
            "exit_code": 124,
            "output": "Timed out while probing this tool.",
            "duration_ms": int((time.time() - started) * 1000),
        }


def _candidate_path(path: Path) -> str | None:
    if path.exists() and os.access(path, os.X_OK):
        return str(path)
    return None


def _find_executable(binary: str) -> str | None:
    resolved = shutil.which(binary)
    if resolved:
        return resolved

    home = Path.home()
    for candidate in (home / ".local" / "bin" / binary, home / "bin" / binary):
        resolved = _candidate_path(candidate)
        if resolved:
            return resolved

    if binary in {"node", "npm", "npx", "playwright", "svgo"}:
        nvm_root = home / ".nvm" / "versions" / "node"
        if nvm_root.exists():
            for version_dir in sorted(nvm_root.iterdir(), key=lambda item: item.name, reverse=True):
                candidate = version_dir / "bin" / binary
                resolved = _candidate_path(candidate)
                if resolved:
                    return resolved

    if binary == "chromium":
        return _candidate_path(Path("/snap/bin/chromium"))

    return None


def _version_probe(
    command_name: str,
    version_args: str = "--version",
    *,
    executable: str | None = None,
) -> dict:
    binary = executable or command_name
    path = _find_executable(binary)
    if not path:
        return {
            "installed": False,
            "command": command_name,
            "path": None,
            "version": None,
            "details": [],
        }

    result = _run_command(f"{shlex.quote(path)} {version_args}")
    version = None
    for line in result["output"].splitlines():
        match = re.search(r"(\d+\.\d+(?:\.\d+)*)", line)
        if match:
            version = match.group(1)
            break

    return {
        "installed": True,
        "command": command_name,
        "path": path,
        "version": version or "Detected",
        "details": [result],
    }


def _flatpak_probe(command_name: str, app_id: str) -> dict:
    flatpak_path = _find_executable("flatpak")
    if not flatpak_path:
        return {
            "installed": False,
            "command": command_name,
            "path": None,
            "version": None,
            "details": [],
        }

    for scope in ("--user", ""):
        scope_arg = f"{scope} " if scope else ""
        result = _run_command(f"{shlex.quote(flatpak_path)} info {scope_arg}{shlex.quote(app_id)}")
        if result["exit_code"] != 0:
            continue

        version = "Detected"
        for line in result["output"].splitlines():
            if line.lower().startswith("version:"):
                version = line.split(":", 1)[1].strip() or "Detected"
                break

        return {
            "installed": True,
            "command": command_name,
            "path": f"flatpak:{app_id}",
            "version": version,
            "details": [result],
        }

    return {
        "installed": False,
        "command": command_name,
        "path": None,
        "version": None,
        "details": [],
    }


@dataclass
class ProbeAgent:
    """A small local execution unit for a category of stack checks."""

    id: str
    title: str
    description: str

    def run(self) -> dict:
        raise NotImplementedError


class EnvironmentAgent(ProbeAgent):
    def run(self) -> dict:
        release = platform.platform()
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "findings": {
                "os": platform.system(),
                "release": release,
                "machine": platform.machine(),
                "python_runtime": platform.python_version(),
                "shell": os.environ.get("SHELL", "unknown"),
                "desktop": os.environ.get("XDG_CURRENT_DESKTOP", "unknown"),
                "session_type": os.environ.get("XDG_SESSION_TYPE", "unknown"),
            },
            "commands": [],
        }


class ToolchainAgent(ProbeAgent):
    def __init__(self, *args, tools: list[dict], **kwargs):
        super().__init__(*args, **kwargs)
        self.tools = tools

    def run(self) -> dict:
        findings = []
        commands = []
        for tool in self.tools:
            if tool.get("probe") == "flatpak":
                probe = _flatpak_probe(tool["command"], tool["app_id"])
            else:
                probe = _version_probe(
                    tool["command"],
                    tool.get("version_args", "--version"),
                    executable=tool.get("executable"),
                )
            findings.append(probe)
            commands.extend(probe.get("details", []))
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "findings": findings,
            "commands": commands,
        }


def build_agents() -> list[ProbeAgent]:
    return [
        EnvironmentAgent(
            id="environment",
            title="Environment Agent",
            description="Profiles the current operating system and session details.",
        ),
        ToolchainAgent(
            id="languages",
            title="Languages Agent",
            description="Checks for language runtimes commonly used in development environments.",
            tools=[
                {"command": "python3", "version_args": "--version"},
                {"command": "node", "version_args": "--version"},
                {"command": "go", "version_args": "version"},
                {"command": "java", "version_args": "-version"},
                {"command": "rustc", "version_args": "--version"},
            ],
        ),
        ToolchainAgent(
            id="package-managers",
            title="Package Managers Agent",
            description="Looks for package management tools used to install dependencies and manage environments.",
            tools=[
                {"command": "pip", "version_args": "--version"},
                {"command": "uv", "version_args": "--version"},
                {"command": "venv", "version_args": "-m venv --help", "executable": "python3"},
                {"command": "npm", "version_args": "--version"},
                {"command": "pnpm", "version_args": "--version"},
                {"command": "cargo", "version_args": "--version"},
            ],
        ),
        ToolchainAgent(
            id="workflow-tools",
            title="Workflow Agent",
            description="Examines source control, automation, container, and editor tools.",
            tools=[
                {"command": "git", "version_args": "--version"},
                {"command": "gh", "version_args": "--version"},
                {"command": "docker", "version_args": "--version"},
                {"command": "make", "version_args": "--version"},
                {"command": "code", "version_args": "--version"},
                {"command": "cursor", "version_args": "--version"},
            ],
        ),
        ToolchainAgent(
            id="creative-tools",
            title="Creative And Browser Agent",
            description="Checks for design, media, browser, and export tools that support mockups, assets, and polished demos.",
            tools=[
                {"command": "inkscape", "version_args": "--version"},
                {"command": "convert", "version_args": "--version"},
                {"command": "magick", "version_args": "--version"},
                {"command": "rsvg-convert", "version_args": "--version"},
                {"command": "ffmpeg", "version_args": "-version"},
                {"command": "chromium", "version_args": "--version"},
                {"command": "flatpak", "version_args": "--version"},
                {"command": "playwright", "version_args": "--version"},
                {"command": "svgo", "version_args": "--version"},
                {"command": "gimp", "probe": "flatpak", "app_id": "org.gimp.GIMP"},
                {"command": "krita", "probe": "flatpak", "app_id": "org.kde.krita"},
            ],
        ),
        ToolchainAgent(
            id="container-tools",
            title="Container Agent",
            description="Checks whether multi-service local container workflows are available.",
            tools=[
                {"command": "docker", "version_args": "--version"},
                {"command": "docker compose", "version_args": "compose version", "executable": "docker"},
            ],
        ),
    ]
