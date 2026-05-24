"""Map Pop/COSMIC action keys to guarded action plans."""

from __future__ import annotations

from .maintenance_actions import attach_action_contract
from .pop_cosmic_deep_scan import run_pop_cosmic_deep_scan


LOW_RISK_ACTIONS = {
    "deep-scan-standard",
    "collect-cosmic-user-logs",
    "collect-display-state",
    "collect-update-state",
    "collect-firmware-visibility",
    "collect-package-state",
    "open-cosmic-settings",
    "open-cosmic-store",
}
BLOCKED_ACTIONS = {
    "apt-repair-step",
    "firmware-review",
    "apply-cosmic-display-layout",
    "manual",
}


def _base_plan(
    *,
    action_key: str,
    title: str,
    risk: str,
    reversible: bool,
    requires_privilege: bool,
    commands: list[str],
    expected_effect: str,
    rollback: list[str],
    verification: list[str],
    summary: str,
) -> dict:
    plan = {
        "id": f"pop-cosmic-{action_key}",
        "family": _family_for_action(action_key),
        "title": title,
        "request": action_key,
        "platform": "Linux",
        "approval_required": True,
        "execution_enabled": False,
        "risk": risk,
        "reversible": reversible,
        "requires_privilege": requires_privilege,
        "summary": summary,
        "commands": commands,
        "manual_steps": verification,
        "expected_effect": expected_effect,
        "rollback": rollback,
        "approval_prompt": "Approve only after reviewing the exact command, side effects, rollback, and verification.",
        "verification": verification,
    }
    return attach_action_contract(plan)


def _family_for_action(action_key: str) -> str:
    if action_key in {"collect-display-state"}:
        return "pop-cosmic-display-evidence"
    if action_key in {"collect-update-state", "collect-package-state", "collect-firmware-visibility"}:
        return "pop-cosmic-update-check"
    if action_key in {"open-cosmic-settings", "open-cosmic-store"}:
        return "pop-cosmic-open-app"
    return "pop-cosmic-deep-scan"


def _blocked_plan(action_key: str, analysis: dict) -> dict:
    title = next(
        (item.get("title") for item in analysis.get("ranked_actions", []) if item.get("action_key") == action_key),
        f"Blocked Pop/COSMIC action: {action_key}",
    )
    return _base_plan(
        action_key=action_key,
        title=title,
        risk="high" if action_key in {"apt-repair-step", "firmware-review"} else "unknown",
        reversible=False,
        requires_privilege=action_key in {"apt-repair-step", "firmware-review"},
        commands=[],
        expected_effect="This action is intentionally blocked until a narrower approved implementation exists.",
        rollback=["No rollback is available because no action is executable yet."],
        verification=["Prepare a narrower action with exact commands, pre-checks, and rollback first."],
        summary=(
            "The agent can recommend this as an escalation path, but this build will not execute it. "
            "Package repair, firmware install/scheduling, release upgrades, refresh, purge, and broad config deletion remain blocked."
        ),
    )


def prepare_pop_cosmic_action(action_key: str, analysis: dict, scan: dict) -> dict:
    if action_key not in LOW_RISK_ACTIONS:
        return _blocked_plan(action_key, analysis)
    if action_key == "open-cosmic-settings":
        return _base_plan(
            action_key=action_key,
            title="Open COSMIC Settings",
            risk="low",
            reversible=True,
            requires_privilege=False,
            commands=["cosmic-settings"],
            expected_effect="Open COSMIC Settings in the current user session.",
            rollback=["Close COSMIC Settings without applying changes."],
            verification=["User confirms whether the relevant setting is visible or behavior changes."],
            summary="Open the official COSMIC Settings app without changing settings automatically.",
        )
    if action_key == "open-cosmic-store":
        return _base_plan(
            action_key=action_key,
            title="Open COSMIC Store",
            risk="low",
            reversible=True,
            requires_privilege=False,
            commands=["cosmic-store"],
            expected_effect="Open COSMIC Store in the current user session.",
            rollback=["Close COSMIC Store without applying updates."],
            verification=["User confirms whether update status or app behavior is visible."],
            summary="Open COSMIC Store without installing or upgrading packages automatically.",
        )
    if action_key == "collect-display-state":
        commands = ["cosmic-randr list", "xrandr --query", "lsusb", "lspci -nnk", "journalctl -b -n 500 --no-pager"]
        return _base_plan(
            action_key=action_key,
            title="Collect COSMIC display evidence",
            risk="low",
            reversible=True,
            requires_privilege=False,
            commands=commands,
            expected_effect="Collect display, dock, GPU, and recent UI log evidence without changing settings.",
            rollback=["No machine change is made."],
            verification=["Review collected output for display names, GPU drivers, dock signals, and UI errors."],
            summary="Bounded read-only display evidence for COSMIC monitor, dock, cursor, and compositor symptoms.",
        )
    if action_key in {"collect-update-state", "collect-package-state"}:
        commands = [
            "apt-get check",
            "apt list --upgradable",
            "apt-mark showhold",
            "apt-cache policy pop-desktop cosmic-session cosmic-comp cosmic-settings cosmic-store",
            "flatpak remote-ls --updates",
        ]
        return _base_plan(
            action_key=action_key,
            title="Collect Pop/COSMIC update evidence",
            risk="low",
            reversible=True,
            requires_privilege=False,
            commands=commands,
            expected_effect="Check package health and visible update state without installing anything.",
            rollback=["No package change is made."],
            verification=["Review apt health, held packages, and visible updates."],
            summary="Bounded read-only update evidence for Pop!_OS and COSMIC package symptoms.",
        )
    if action_key == "collect-firmware-visibility":
        return _base_plan(
            action_key=action_key,
            title="Collect firmware visibility",
            risk="low",
            reversible=True,
            requires_privilege=False,
            commands=["fwupdmgr get-updates", "system76-firmware-cli info"],
            expected_effect="List firmware visibility without scheduling or installing firmware updates.",
            rollback=["No firmware change is made."],
            verification=["Review visible firmware update state and schedule any install through a separate high-risk flow."],
            summary="Read-only firmware visibility for System76/Pop!_OS troubleshooting.",
        )
    return _base_plan(
        action_key="deep-scan-standard",
        title="Run Pop/COSMIC deep scan",
        risk="low",
        reversible=True,
        requires_privilege=False,
        commands=["journalctl --user -b --no-pager -n 500", "systemctl --user --failed --no-legend --plain"],
        expected_effect="Collect standard Pop!_OS/COSMIC evidence without changing the machine.",
        rollback=["No machine change is made."],
        verification=["Review the deep scan findings."],
        summary="Read-only standard Pop!_OS/COSMIC evidence collection.",
    )


def prepare_verification_plan(action_result: dict, original_scan: dict) -> dict:
    scope = "updates" if "update" in " ".join(action_result.get("commands", [])).lower() else "standard"
    return run_pop_cosmic_deep_scan(scope)


def prepare_rollback_plan(action_result: dict) -> dict:
    rollback = action_result.get("rollback", [])
    return {
        "available": bool(rollback),
        "steps": rollback,
        "message": "Rollback is manual for the current MVP unless an exact rollback command was recorded before execution.",
    }
