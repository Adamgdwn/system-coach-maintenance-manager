"""Approval-required plans for user-requested system changes."""

from __future__ import annotations

import platform
import re


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _cursor_direction(text: str) -> str:
    if any(word in text for word in ("smaller", "small", "shrink", "decrease", "reduce", "lower")):
        return "smaller"
    if any(word in text for word in ("bigger", "larger", "large", "increase", "grow", "huge")):
        return "larger"
    return "adjust"


def _linux_desktop_family(distribution_hint: str | None) -> str:
    hint = (distribution_hint or "").lower()
    if "cosmic" in hint:
        return "cosmic"
    if "gnome" in hint or "ubuntu" in hint:
        return "gnome-compatible"
    if "kde" in hint or "plasma" in hint:
        return "kde"
    if "xfce" in hint or "xubuntu" in hint:
        return "xfce"
    return "unknown"


def _linux_cursor_commands(target_size: str, desktop_family: str) -> list[str]:
    if desktop_family == "gnome-compatible":
        return [
            "gsettings get org.gnome.desktop.interface cursor-size",
            f"gsettings set org.gnome.desktop.interface cursor-size {target_size}",
        ]
    if desktop_family == "xfce":
        return [
            "xfconf-query -c xsettings -p /Gtk/CursorThemeSize",
            f"xfconf-query -c xsettings -p /Gtk/CursorThemeSize -s {target_size}",
        ]
    if desktop_family == "kde":
        return [
            "kcmshell6 cursors",
            "kcmshell5 cursors",
        ]
    if desktop_family == "cosmic":
        return [
            "cosmic-settings",
        ]
    return [
        "gsettings get org.gnome.desktop.interface cursor-size",
        "xfconf-query -c xsettings -p /Gtk/CursorThemeSize",
    ]


def _linux_cursor_manual_steps(desktop_family: str) -> list[str]:
    if desktop_family == "gnome-compatible":
        return [
            "Open Settings > Accessibility > Seeing, or the desktop appearance settings if available.",
            "Change cursor size one step at a time and confirm it looks right across normal apps.",
            "Record the previous cursor size before approving a command-based change.",
        ]
    if desktop_family == "kde":
        return [
            "Open System Settings > Appearance > Cursors.",
            "Select the desired cursor size from the cursor theme options, then apply it.",
            "Use the same panel to restore the previous cursor size if needed.",
        ]
    if desktop_family == "xfce":
        return [
            "Open Settings Manager > Mouse and Touchpad or Appearance, depending on the distribution.",
            "Adjust pointer/cursor size one step at a time and test normal apps.",
            "Record the previous Xfce cursor value before approving a command-based change.",
        ]
    if desktop_family == "cosmic":
        return [
            "Open COSMIC Settings and inspect accessibility, appearance, and mouse or pointer options.",
            "Change pointer size one step at a time and test normal apps.",
            "Use the same settings panel to restore the previous cursor size if needed.",
        ]
    return [
        "Open the desktop appearance, accessibility, or mouse/pointer settings.",
        "Confirm whether the session is GNOME, KDE Plasma, Xfce, COSMIC, or another desktop.",
        "Change pointer size one step at a time and confirm it looks right across normal apps.",
    ]


def _linux_cursor_plan(request_text: str, distribution_hint: str | None = None) -> dict:
    direction = _cursor_direction(_normalize(request_text))
    target_size = "24" if direction == "smaller" else "48" if direction == "larger" else "<size>"
    desktop_family = _linux_desktop_family(distribution_hint)
    hint_note = f" Desktop hint: {distribution_hint}." if distribution_hint else " Desktop hint: unknown."
    return {
        "id": "request-cursor-size-linux",
        "title": f"Adjust Linux cursor size ({direction})",
        "request": request_text,
        "platform": "Linux",
        "approval_required": True,
        "execution_enabled": False,
        "risk": "low",
        "reversible": True,
        "requires_privilege": False,
        "summary": (
            "Prepare a user-session cursor size change. The plan uses the detected desktop session "
            "when possible and does not modify system-wide files." + hint_note
        ),
        "commands": _linux_cursor_commands(target_size, desktop_family),
        "manual_steps": _linux_cursor_manual_steps(desktop_family),
        "expected_effect": "Change only the current user's pointer size setting.",
        "rollback": [
            "Set the cursor size back to the previous value recorded by the first get command.",
            "If the command does not apply to this desktop environment, revert through the desktop settings UI.",
        ],
        "approval_prompt": "Approve only after confirming the desktop environment and target cursor size.",
    }


def _windows_cursor_plan(request_text: str) -> dict:
    direction = _cursor_direction(_normalize(request_text))
    return {
        "id": "request-cursor-size-windows",
        "title": f"Adjust Windows cursor size ({direction})",
        "request": request_text,
        "platform": "Windows",
        "approval_required": True,
        "execution_enabled": False,
        "risk": "low",
        "reversible": True,
        "requires_privilege": False,
        "summary": "Prepare a current-user pointer size change through Windows Accessibility settings.",
        "commands": [
            "start ms-settings:easeofaccess-mousepointer",
            "powershell -NoProfile -Command \"Start-Process ms-settings:easeofaccess-mousepointer\"",
        ],
        "manual_steps": [
            "Open Settings > Accessibility > Mouse pointer and touch.",
            "Move the Size slider smaller or larger, then test it in normal windows.",
            "Use the same settings page to restore the previous size if the result feels wrong.",
        ],
        "expected_effect": "Open the Windows pointer settings page so the user can adjust the current user's cursor size.",
        "rollback": ["Return to the same settings page and move the Size slider back to the prior value."],
        "approval_prompt": "Approve opening the settings page only when you are ready to adjust the pointer size manually.",
    }


def _unsupported_request_plan(request_text: str, os_name: str) -> dict:
    return {
        "id": "request-needs-triage",
        "title": "Request needs troubleshooting triage",
        "request": request_text,
        "platform": os_name,
        "approval_required": True,
        "execution_enabled": False,
        "risk": "unknown",
        "reversible": False,
        "requires_privilege": False,
        "summary": "This request does not match a built-in plan yet. The assistant should ask clarifying questions and prepare a narrow plan before execution.",
        "commands": [],
        "manual_steps": [
            "Clarify the exact symptom and target application or setting.",
            "Collect read-only diagnostics relevant to that symptom.",
            "Prepare a concrete plan with commands, risk, reversibility, and approval requirements.",
        ],
        "expected_effect": "Turn an open-ended request into a safe, reviewable maintenance plan.",
        "rollback": ["No change is proposed yet, so no rollback is required."],
        "approval_prompt": "Do not execute anything until this request has a concrete plan.",
    }


def prepare_request_plan(request_text: str, os_name: str | None = None, distribution_hint: str | None = None) -> dict:
    """Turn a user maintenance request into an approval-required plan preview."""

    resolved_os = os_name or platform.system() or "Unknown"
    normalized = _normalize(request_text)
    if not normalized:
        return _unsupported_request_plan(request_text, resolved_os)

    if "cursor" in normalized or "pointer" in normalized:
        if resolved_os.lower().startswith("win"):
            return _windows_cursor_plan(request_text)
        if resolved_os.lower() == "linux":
            return _linux_cursor_plan(request_text, distribution_hint=distribution_hint)

    return _unsupported_request_plan(request_text, resolved_os)


def format_request_plan(plan: dict) -> str:
    lines = [
        plan["title"],
        f"Platform: {plan['platform']}",
        f"Risk: {plan['risk']}",
        f"Requires privilege: {plan['requires_privilege']}",
        f"Reversible: {plan['reversible']}",
        f"Approval required: {plan['approval_required']}",
        f"Execution enabled: {plan['execution_enabled']}",
        "",
        plan["summary"],
        "",
        "Commands:",
    ]
    lines.extend(f"- {command}" for command in plan.get("commands", []))
    if not plan.get("commands"):
        lines.append("- No commands prepared yet.")
    lines.extend(["", "Manual steps:"])
    lines.extend(f"- {step}" for step in plan.get("manual_steps", []))
    lines.extend(["", f"Expected effect: {plan['expected_effect']}", "", "Rollback:"])
    lines.extend(f"- {step}" for step in plan.get("rollback", []))
    lines.extend(["", f"Approval gate: {plan['approval_prompt']}"])
    return "\n".join(lines)
