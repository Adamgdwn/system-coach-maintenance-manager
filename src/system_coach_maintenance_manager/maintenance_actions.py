"""Approved-action contracts and guarded command execution."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess


DEFAULT_TIMEOUT_SECONDS = 30
CONTRACT_VERSION = "approved-action-contract-v1"
MAX_OUTPUT_BYTES = 20000
ALLOWED_RISKS = {"low", "medium", "high"}
LOW_RISK_FAMILIES = {
    "cursor-size",
    "display-brightness",
    "display-dock",
    "display-layout-fix",
    "display-night-light",
    "display-refresh-rate",
    "display-scaling",
    "audio-routing",
    "failed-services",
    "journal-errors",
    "network-basics",
    "pop-cosmic-deep-scan",
    "pop-cosmic-display-evidence",
    "pop-cosmic-open-app",
    "pop-cosmic-update-check",
}
ELEVATED_FAMILIES = {
    "failed-services",
    "journal-errors",
    "network-basics",
    "network-dns",
    "package-manager-health",
    "package-updates",
    "pop-cosmic-apt-update",
    "pop-cosmic-package-repair",
    "pop-cosmic-firmware-review",
    "startup-apps",
}
ALLOWED_EXECUTABLES = {
    "apt",
    "apt-cache",
    "apt-get",
    "apt-mark",
    "brightnessctl",
    "cat",
    "choco",
    "cmd",
    "cosmic-randr",
    "cosmic-settings",
    "cosmic-store",
    "dnf",
    "dpkg",
    "dpkg-query",
    "eventvwr.msc",
    "flatpak",
    "fwupdmgr",
    "gsettings",
    "ip",
    "ipconfig",
    "journalctl",
    "kcmshell5",
    "kcmshell6",
    "kscreen-doctor",
    "lspci",
    "lsusb",
    "pgrep",
    "pop-upgrade",
    "pactl",
    "pacman",
    "powershell",
    "pwsh",
    "resolvectl",
    "route",
    "stat",
    "system76-firmware-cli",
    "systemctl",
    "wevtutil",
    "winget",
    "xfconf-query",
    "xrandr",
}
READ_ONLY_VERBS = {"get", "info", "list", "query"}
MUTATING_VERBS = {"set"}


def _now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "action"


def load_runner_controls(project_control_path: Path | None = None) -> dict:
    """Read the small subset of project controls needed by the runner gate."""

    path = project_control_path or Path.cwd() / "project-control.yaml"
    controls = {
        "governance_level": None,
        "autonomy_level": None,
        "action_runner_enabled": False,
        "elevated_action_runner_enabled": False,
        "source": str(path),
    }
    if not path.exists():
        controls["gate_reason"] = "project-control.yaml was not found, so action execution is disabled."
        return controls

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("governance_level:"):
            raw_value = stripped.split(":", 1)[1].strip()
            try:
                controls["governance_level"] = int(raw_value)
            except ValueError:
                controls["governance_level"] = None
        elif stripped.startswith("autonomy_level:"):
            controls["autonomy_level"] = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("action_runner_enabled:"):
            raw_value = stripped.split(":", 1)[1].strip().lower()
            controls["action_runner_enabled"] = raw_value in {"true", "yes", "1"}
        elif stripped.startswith("elevated_action_runner_enabled:"):
            raw_value = stripped.split(":", 1)[1].strip().lower()
            controls["elevated_action_runner_enabled"] = raw_value in {"true", "yes", "1"}
    return controls


def _has_placeholder(command: str) -> bool:
    return "<" in command or ">" in command


def _candidate_assessment(plan: dict) -> dict:
    commands = plan.get("commands", [])
    family = plan.get("family", plan.get("finding_id", "maintenance"))
    requires_privilege = bool(plan.get("requires_privilege"))
    risk = plan.get("risk")
    reasons = []
    if not plan.get("approval_required", True):
        reasons.append("plan does not require approval")
    if not commands:
        reasons.append("plan has no exact command preview")
    if any(_has_placeholder(command) for command in commands):
        reasons.append("plan contains placeholder command text")

    if requires_privilege:
        execution_mode = "elevated"
        if risk not in ALLOWED_RISKS:
            reasons.append("elevated plan risk must be low, medium, or high")
        if family not in ELEVATED_FAMILIES:
            reasons.append("plan family is not in the elevated guarded catalog")
    else:
        execution_mode = "user"
        if risk != "low":
            reasons.append("user-level guarded execution requires low risk")
        if not plan.get("reversible"):
            reasons.append("user-level guarded execution requires a reversible plan")
        if family not in LOW_RISK_FAMILIES:
            reasons.append("plan family is not in the low-risk guarded catalog")

    for command in commands:
        allowed, reason = _command_allowed(command, family, requires_privilege=requires_privilege)
        if not allowed:
            reasons.append(reason or f"command is not allowed: {command}")
    return {
        "eligible": not reasons,
        "reasons": reasons,
        "family": family,
        "execution_mode": execution_mode,
    }


def _execution_gate(controls: dict, assessment: dict) -> dict:
    reasons = []
    governance_level = controls.get("governance_level")
    autonomy_level = controls.get("autonomy_level")
    if governance_level != 1:
        reasons.append("guarded execution currently requires governance level 1 approval controls")
    if autonomy_level != "A1":
        reasons.append("guarded execution currently requires A1 user-approved autonomy")
    if not controls.get("action_runner_enabled"):
        reasons.append("action_runner_enabled is not set in project controls")
    if assessment["execution_mode"] == "elevated" and not controls.get("elevated_action_runner_enabled"):
        reasons.append("elevated_action_runner_enabled is not set in project controls")
    if not assessment["eligible"]:
        reasons.extend(assessment["reasons"])
    return {
        "allowed": not reasons,
        "reasons": reasons,
    }


def _split_command(command: str) -> list[str]:
    return shlex.split(command, posix=os.name != "nt")


def _command_allowed(command: str, family: str, *, requires_privilege: bool = False) -> tuple[bool, str | None]:
    try:
        parts = _split_command(command)
    except ValueError as exc:
        return False, f"command could not be parsed safely: {exc}"
    if not parts:
        return False, "empty command"
    executable = Path(parts[0]).name.lower()
    if executable not in ALLOWED_EXECUTABLES:
        return False, f"executable {parts[0]} is not in the guarded catalog"
    if executable in {"gsettings", "xfconf-query"}:
        if not any(verb in parts for verb in READ_ONLY_VERBS | MUTATING_VERBS) and "-s" not in parts:
            return False, f"{executable} command does not declare an allowed read or set operation"
    if family.startswith("pop-cosmic"):
        joined = " ".join(parts).lower()
        blocked_terms = (" full-upgrade", " install", " remove", " purge", " autoremove", " release upgrade", " recovery upgrade")
        if any(term in f" {joined}" for term in blocked_terms):
            return False, "Pop/COSMIC guarded actions block package mutation, release upgrades, purge, and autoremove by default"
        if executable in {"apt", "apt-get"} and not any(term in parts for term in {"check", "list"}):
            return False, "Pop/COSMIC apt commands are limited to read-only check/list operations in this catalog"
        if executable == "apt-cache" and "policy" not in parts:
            return False, "Pop/COSMIC apt-cache commands are limited to policy checks"
        if executable == "apt-mark" and "showhold" not in parts:
            return False, "Pop/COSMIC apt-mark commands are limited to showhold"
        if executable == "flatpak" and not (("remote-ls" in parts and "--updates" in parts) or "remotes" in parts or "list" in parts):
            return False, "Pop/COSMIC flatpak commands are limited to listing operations"
        if executable == "fwupdmgr" and "get-updates" not in parts:
            return False, "Pop/COSMIC firmware commands are limited to get-updates"
        if executable == "pop-upgrade" and "status" not in parts:
            return False, "Pop/COSMIC pop-upgrade commands are limited to status checks"
    if executable in {"cmd", "powershell", "pwsh"} and not requires_privilege and family not in {"cursor-size", "display-dock", "journal-errors", "network-basics"}:
        return False, f"{executable} execution is only enabled for guarded settings or read-only evidence plans"
    return True, None


def _elevation_prompt() -> dict:
    if os.name == "nt":
        return {
            "method": "windows-uac",
            "message": "Windows will show a UAC prompt for this elevated action.",
        }
    return {
        "method": "pkexec",
        "available": shutil.which("pkexec") is not None,
        "message": "Linux will show a Polkit password prompt through pkexec for this elevated action.",
    }


def build_action_contract(plan: dict, project_control_path: Path | None = None) -> dict:
    """Build the immutable preview contract for a plan."""

    controls = load_runner_controls(project_control_path)
    assessment = _candidate_assessment(plan)
    gate = _execution_gate(controls, assessment)
    action_id = f"action-{_slug(plan.get('id', plan.get('title', 'plan')))}"
    contract = {
        "contract_version": CONTRACT_VERSION,
        "id": action_id,
        "plan_id": plan.get("id"),
        "plan_title": plan.get("title"),
        "family": assessment["family"],
        "status": "blocked",
        "eligible_for_guarded_execution": assessment["eligible"],
        "eligibility_notes": assessment["reasons"],
        "approval_required": True,
        "confirmation_phrase": "APPROVE",
        "execution_enabled": gate["allowed"],
        "execution_mode": assessment["execution_mode"],
        "elevation_prompt": _elevation_prompt() if assessment["execution_mode"] == "elevated" else None,
        "execution_gate": gate,
        "command_preview": list(plan.get("commands", [])),
        "expected_effect": plan.get("expected_effect", ""),
        "requires_privilege": bool(plan.get("requires_privilege")),
        "reversible": bool(plan.get("reversible")),
        "risk": plan.get("risk", "unknown"),
        "timeout_seconds": DEFAULT_TIMEOUT_SECONDS,
        "output_capture": {
            "stdout": True,
            "stderr": True,
            "max_bytes": MAX_OUTPUT_BYTES,
        },
        "post_check": _post_check_for_plan(plan),
        "rollback": list(plan.get("rollback", [])),
        "created_at": _now(),
    }
    contract["fingerprint"] = action_contract_fingerprint(contract)
    return contract


def action_contract_fingerprint(contract: dict) -> str:
    """Return a stable short fingerprint for the executable action preview."""

    material = {
        "action_id": contract.get("id"),
        "title": contract.get("plan_title"),
        "risk": contract.get("risk"),
        "execution_mode": contract.get("execution_mode"),
        "command_preview": list(contract.get("command_preview", [])),
        "confirmation_phrase": contract.get("confirmation_phrase"),
        "rollback": list(contract.get("rollback", [])),
        "verification_command": list(contract.get("post_check", [])),
    }
    digest = hashlib.sha256(json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    return digest[:16]


def _post_check_for_plan(plan: dict) -> list[str]:
    family = plan.get("family", "")
    if family == "cursor-size":
        return ["Read the current cursor size setting again.", "Confirm normal apps render the pointer as expected."]
    if family.startswith("display-"):
        return ["Confirm the target display uses the intended setting.", "Confirm text and windows are usable."]
    if family == "audio-routing":
        return ["Play test audio or record a short microphone test.", "Confirm the expected device is selected."]
    return ["Rerun the relevant diagnostic or request review before considering the action complete."]


def build_action_contracts(plans: list[dict], project_control_path: Path | None = None) -> list[dict]:
    return [build_action_contract(plan, project_control_path=project_control_path) for plan in plans]


def attach_action_contract(plan: dict, project_control_path: Path | None = None) -> dict:
    contract = build_action_contract(plan, project_control_path=project_control_path)
    plan["action_contract"] = contract
    plan["execution_enabled"] = contract["execution_enabled"]
    return plan


def execute_guarded_action(contract: dict, confirmation_text: str) -> dict:
    """Execute a gated low-risk action contract."""

    started_at = _now()

    if not contract.get("execution_enabled"):
        return {
            "action_id": contract.get("id"),
            "plan_id": contract.get("plan_id"),
            "status": "blocked",
            "started_at": started_at,
            "finished_at": _now(),
            "execution_enabled": False,
            "exit_code": None,
            "commands": contract.get("command_preview", []),
            "output": "",
            "error": "; ".join(contract.get("execution_gate", {}).get("reasons", [])),
            "post_check": contract.get("post_check", []),
            "rollback": contract.get("rollback", []),
        }

    expected_confirmation = str(contract.get("confirmation_phrase", "")).strip()
    provided_confirmation = str(confirmation_text or "").strip()
    if contract.get("approval_required", True) and (not expected_confirmation or provided_confirmation != expected_confirmation):
        return {
            "action_id": contract.get("id"),
            "plan_id": contract.get("plan_id"),
            "status": "blocked",
            "started_at": started_at,
            "finished_at": _now(),
            "execution_enabled": True,
            "exit_code": None,
            "commands": contract.get("command_preview", []),
            "output": "",
            "error": "approval confirmation phrase did not match",
            "post_check": contract.get("post_check", []),
            "rollback": contract.get("rollback", []),
        }

    outputs = []
    commands = contract.get("command_preview", [])
    family = contract.get("family", "")
    requires_privilege = contract.get("execution_mode") == "elevated" or bool(contract.get("requires_privilege"))
    for command in commands:
        allowed, reason = _command_allowed(command, family, requires_privilege=requires_privilege)
        if not allowed:
            return {
                "action_id": contract.get("id"),
                "plan_id": contract.get("plan_id"),
                "status": "blocked",
                "started_at": started_at,
                "finished_at": _now(),
                "execution_enabled": True,
                "exit_code": None,
                "commands": commands,
                "output": "\n".join(outputs),
                "error": reason or "command is not allowed",
                "post_check": contract.get("post_check", []),
                "rollback": contract.get("rollback", []),
            }
        try:
            command_parts = _split_command(command)
            if requires_privilege:
                command_parts = _elevated_command_parts(command_parts)
            completed = subprocess.run(
                command_parts,
                capture_output=True,
                check=False,
                text=True,
                timeout=int(contract.get("timeout_seconds") or DEFAULT_TIMEOUT_SECONDS),
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return {
                "action_id": contract.get("id"),
                "plan_id": contract.get("plan_id"),
                "status": "failed",
                "started_at": started_at,
                "finished_at": _now(),
                "execution_enabled": True,
                "exit_code": None,
                "commands": commands,
                "output": "\n".join(outputs),
                "error": str(exc),
                "post_check": contract.get("post_check", []),
                "rollback": contract.get("rollback", []),
            }
        output = "\n".join(part for part in (completed.stdout, completed.stderr) if part).strip()
        if output:
            outputs.append(f"$ {command}\n{output[:MAX_OUTPUT_BYTES]}")
        if completed.returncode != 0:
            return {
                "action_id": contract.get("id"),
                "plan_id": contract.get("plan_id"),
                "status": "failed",
                "started_at": started_at,
                "finished_at": _now(),
                "execution_enabled": True,
                "exit_code": completed.returncode,
                "commands": commands,
                "output": "\n".join(outputs),
                "error": f"command failed: {command}",
                "post_check": contract.get("post_check", []),
                "rollback": contract.get("rollback", []),
            }

    return {
        "action_id": contract.get("id"),
        "plan_id": contract.get("plan_id"),
        "status": "completed",
        "started_at": started_at,
        "finished_at": _now(),
        "execution_enabled": True,
        "exit_code": 0,
        "commands": commands,
        "output": "\n".join(outputs),
        "error": "",
        "post_check": contract.get("post_check", []),
        "rollback": contract.get("rollback", []),
    }


def _elevated_command_parts(parts: list[str]) -> list[str]:
    if os.name == "nt":
        exe = parts[0]
        args = " ".join(shlex.quote(part) for part in parts[1:])
        script = f"Start-Process -FilePath {exe!r} -ArgumentList {args!r} -Verb RunAs -Wait"
        shell = "powershell"
        return [shell, "-NoProfile", "-Command", script]

    if not shutil.which("pkexec"):
        raise OSError("pkexec is not available; install/configure Polkit or run the command manually with administrator rights")
    return ["pkexec", *parts]
