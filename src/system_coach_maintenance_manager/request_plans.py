"""Approval-required plans for user-requested system changes."""

from __future__ import annotations

import platform
import re

from .followup_plans import build_cosmic_display_layout_request_from_intent
from .maintenance_actions import attach_action_contract

SUPPORTED_FAMILY_OVERRIDES = {
    "cursor-size",
    "display",
    "display-dock",
    "display-layout-fix",
    "audio-routing",
    "network-dns",
    "package-updates",
    "pop-cosmic",
    "docker-cleanup",
    "startup-apps",
    "slow-computer",
    "unknown",
}

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


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _platform_key(os_name: str | None) -> str:
    normalized = (os_name or "").strip().lower()
    if normalized.startswith("win"):
        return "windows"
    if normalized == "linux":
        return "linux"
    return "unknown"


def _platform_label(platform_key: str, fallback: str) -> str:
    if platform_key == "windows":
        return "Windows"
    if platform_key == "linux":
        return "Linux"
    return fallback or "Unknown"


def _has_any(text: str, words: tuple[str, ...]) -> bool:
    return any(word in text for word in words)


def _is_display_dock_request(text: str) -> bool:
    display_terms = (
        "display",
        "monitor",
        "screen",
        "external",
        "right screen",
        "far right",
        "rotated",
        "rotation",
        "half the screen",
        "bottom half",
    )
    dock_terms = ("dock", "docking", "dell", "displaylink", "usb-c", "thunderbolt")
    behavior_terms = ("jitter", "jittery", "cursor", "pointer", "hides", "hidden", "loses", "disappear")
    return (
        _has_any(text, display_terms)
        and (_has_any(text, dock_terms) or _has_any(text, behavior_terms) or _has_any(text, ("rotated", "rotation")))
    )


def _cursor_direction(text: str) -> str:
    if _has_any(text, ("smaller", "small", "shrink", "decrease", "reduce", "lower")):
        return "smaller"
    if _has_any(text, ("bigger", "larger", "large", "increase", "grow", "huge")):
        return "larger"
    return "adjust"


def _request_plan(
    *,
    plan_id: str,
    family: str,
    title: str,
    request_text: str,
    platform_name: str,
    risk: str,
    reversible: bool,
    requires_privilege: bool,
    summary: str,
    commands: list[str],
    manual_steps: list[str],
    expected_effect: str,
    rollback: list[str],
    approval_prompt: str,
) -> dict:
    return attach_action_contract({
        "id": plan_id,
        "family": family,
        "title": title,
        "request": request_text,
        "platform": platform_name,
        "approval_required": True,
        "execution_enabled": False,
        "risk": risk,
        "reversible": reversible,
        "requires_privilege": requires_privilege,
        "summary": summary,
        "commands": commands,
        "manual_steps": manual_steps,
        "expected_effect": expected_effect,
        "rollback": rollback,
        "approval_prompt": approval_prompt,
    })


def _triage_plan(request_text: str, os_name: str, family: str = "unknown") -> dict:
    return _request_plan(
        plan_id="request-needs-triage" if family == "unknown" else f"request-{family}-triage",
        family=family,
        title="Request needs troubleshooting triage",
        request_text=request_text,
        platform_name=os_name,
        risk="unknown",
        reversible=False,
        requires_privilege=False,
        summary=(
            "This request needs a narrower troubleshooting path before commands are useful. "
            "The assistant should clarify the target setting, symptom, platform, and rollback expectation."
        ),
        commands=[],
        manual_steps=[
            "Clarify the exact symptom and target application, device, service, or setting.",
            "Collect read-only diagnostics relevant to that symptom.",
            "Prepare a concrete plan with commands, risk, reversibility, and approval requirements.",
        ],
        expected_effect="Turn an open-ended request into a safe, reviewable maintenance plan.",
        rollback=["No change is proposed yet, so no rollback is required."],
        approval_prompt="Do not execute anything until this request has a concrete plan.",
    )


def _unsupported_platform_plan(request_text: str, os_name: str, family: str) -> dict:
    plan = _triage_plan(request_text, os_name, family)
    plan["summary"] = (
        f"The request matched the {family} family, but this operating system is not supported by "
        "a built-in command plan yet. Keep this as a manual triage record until platform support exists."
    )
    plan["expected_effect"] = "Avoid guessing at machine-specific maintenance commands on an unsupported platform."
    return plan


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
        return ["kcmshell6 cursors", "kcmshell5 cursors"]
    if desktop_family == "cosmic":
        return ["cosmic-settings"]
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


def _cursor_plan(request_text: str, platform_name: str, platform_key: str, distribution_hint: str | None) -> dict:
    direction = _cursor_direction(_normalize(request_text))
    target_size = "24" if direction == "smaller" else "48" if direction == "larger" else "<size>"
    if platform_key == "linux":
        desktop_family = _linux_desktop_family(distribution_hint)
        hint_note = f" Desktop hint: {distribution_hint}." if distribution_hint else " Desktop hint: unknown."
        return _request_plan(
            plan_id="request-cursor-size-linux",
            family="cursor-size",
            title=f"Adjust Linux cursor size ({direction})",
            request_text=request_text,
            platform_name=platform_name,
            risk="low",
            reversible=True,
            requires_privilege=False,
            summary=(
                "Prepare a user-session cursor size change. The plan uses the detected desktop session "
                "when possible and does not modify system-wide files." + hint_note
            ),
            commands=_linux_cursor_commands(target_size, desktop_family),
            manual_steps=_linux_cursor_manual_steps(desktop_family),
            expected_effect="Change only the current user's pointer size setting.",
            rollback=[
                "Set the cursor size back to the previous value recorded by the first get command.",
                "If the command does not apply to this desktop environment, revert through the desktop settings UI.",
            ],
            approval_prompt="Approve only after confirming the desktop environment and target cursor size.",
        )

    if platform_key == "windows":
        return _request_plan(
            plan_id="request-cursor-size-windows",
            family="cursor-size",
            title=f"Adjust Windows cursor size ({direction})",
            request_text=request_text,
            platform_name=platform_name,
            risk="low",
            reversible=True,
            requires_privilege=False,
            summary="Prepare a current-user pointer size change through Windows Accessibility settings.",
            commands=[
                'cmd /c start "" ms-settings:easeofaccess-mousepointer',
                'powershell -NoProfile -Command "Start-Process ms-settings:easeofaccess-mousepointer"',
            ],
            manual_steps=[
                "Open Settings > Accessibility > Mouse pointer and touch.",
                "Move the Size slider smaller or larger, then test it in normal windows.",
                "Use the same settings page to restore the previous size if the result feels wrong.",
            ],
            expected_effect="Open the Windows pointer settings page so the user can adjust the current user's cursor size.",
            rollback=["Return to the same settings page and move the Size slider back to the prior value."],
            approval_prompt="Approve opening the settings page only when you are ready to adjust the pointer size manually.",
        )

    return _unsupported_platform_plan(request_text, platform_name, "cursor-size")


def _display_plan(request_text: str, platform_name: str, platform_key: str) -> dict:
    normalized = _normalize(request_text)
    if _has_any(normalized, ("brightness", "dim", "brighter")):
        title = "Plan a brightness adjustment"
        family = "display-brightness"
        linux_commands = ["brightnessctl info", "ls /sys/class/backlight"]
        windows_commands = [
            "start ms-settings:display",
            'powershell -NoProfile -Command "Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightness"',
        ]
        expected = "Inspect current brightness controls before changing the active display brightness."
    elif _has_any(normalized, ("night light", "nightlight", "blue light", "warm")):
        title = "Plan a night light adjustment"
        family = "display-night-light"
        linux_commands = [
            "gsettings get org.gnome.settings-daemon.plugins.color night-light-enabled",
            "gsettings get org.gnome.settings-daemon.plugins.color night-light-temperature",
        ]
        windows_commands = ["start ms-settings:nightlight"]
        expected = "Open or inspect night light settings before changing color temperature or schedule."
    elif _has_any(normalized, ("refresh", "hz", "hertz")):
        title = "Plan a refresh-rate adjustment"
        family = "display-refresh-rate"
        linux_commands = ["xrandr --query", "kscreen-doctor -o"]
        windows_commands = [
            "start ms-settings:display-advanced",
            'powershell -NoProfile -Command "Get-CimInstance Win32_VideoController | Select-Object Name,CurrentRefreshRate"',
        ]
        expected = "Inspect supported display modes before changing refresh rate."
    else:
        title = "Plan a display scaling adjustment"
        family = "display-scaling"
        linux_commands = ["xrandr --query", "gsettings get org.gnome.desktop.interface scaling-factor"]
        windows_commands = [
            "start ms-settings:display",
            'powershell -NoProfile -Command "Get-CimInstance Win32_VideoController | Select-Object Name,CurrentHorizontalResolution,CurrentVerticalResolution"',
        ]
        expected = "Inspect current display settings before changing scale or resolution."

    if platform_key == "linux":
        return _request_plan(
            plan_id=f"request-{family}-linux",
            family=family,
            title=f"{title} on Linux",
            request_text=request_text,
            platform_name=platform_name,
            risk="low",
            reversible=True,
            requires_privilege=False,
            summary="Prepare a user-session display change and collect current mode evidence first.",
            commands=linux_commands,
            manual_steps=[
                "Confirm the active monitor and current display mode.",
                "Change one display setting at a time from the desktop settings panel.",
                "Wait for the desktop confirmation prompt before accepting the new mode.",
            ],
            expected_effect=expected,
            rollback=["Use the desktop display settings panel to restore the previous value."],
            approval_prompt="Approve only after confirming the target monitor and previous setting.",
        )

    if platform_key == "windows":
        return _request_plan(
            plan_id=f"request-{family}-windows",
            family=family,
            title=f"{title} on Windows",
            request_text=request_text,
            platform_name=platform_name,
            risk="low",
            reversible=True,
            requires_privilege=False,
            summary="Prepare a current-user display settings change through Windows Settings.",
            commands=windows_commands,
            manual_steps=[
                "Open Windows display settings for the active monitor.",
                "Record the current scale, brightness, night light, or refresh-rate value.",
                "Apply one change at a time and use the confirmation prompt to revert if needed.",
            ],
            expected_effect=expected,
            rollback=["Return to the same Windows Settings page and restore the previous value."],
            approval_prompt="Approve only after confirming the target monitor and previous setting.",
        )

    return _unsupported_platform_plan(request_text, platform_name, family)


def _display_dock_plan(request_text: str, platform_name: str, platform_key: str, distribution_hint: str | None) -> dict:
    desktop_family = _linux_desktop_family(distribution_hint)
    if platform_key == "linux":
        commands = ["xrandr --query", "lsusb", "lspci", "journalctl -b -n 500 --no-pager"]
        if desktop_family == "cosmic" or _has_any(_normalize(distribution_hint or ""), ("cosmic", "pop")):
            commands.insert(0, "cosmic-randr list")
        return _request_plan(
            plan_id="request-display-dock-linux",
            family="display-dock",
            title="Investigate Linux display, dock, and pointer behavior",
            request_text=request_text,
            platform_name=platform_name,
            risk="low",
            reversible=True,
            requires_privilege=False,
            summary=(
                "This is a display topology and dock investigation, not a cursor-size change. "
                "The plan collects monitor layout, rotation, dock hardware, GPU, and recent compositor/session log evidence "
                "before proposing any display fix."
            ),
            commands=commands,
            manual_steps=[
                "Identify the affected physical monitor, connector name, rotation, scale, refresh rate, and position.",
                "Confirm whether the affected monitor is routed through a USB-C, Thunderbolt, or DisplayLink dock.",
                "Review compositor/session log evidence for rendering, cursor, hotplug, or mode-setting errors.",
                "Prepare a separate approved fix only after the evidence names a target setting or driver path.",
            ],
            expected_effect=(
                "Collect read-only evidence for rotated external monitor, dock, hidden desktop area, and jittery pointer symptoms."
            ),
            rollback=["No setting is changed by this investigation; close the evidence window to stop here."],
            approval_prompt="Approve this evidence collection before any display setting or driver change is proposed.",
        )

    if platform_key == "windows":
        return _request_plan(
            plan_id="request-display-dock-windows",
            family="display-dock",
            title="Investigate Windows display, dock, and pointer behavior",
            request_text=request_text,
            platform_name=platform_name,
            risk="low",
            reversible=True,
            requires_privilege=False,
            summary=(
                "This is a display topology and dock investigation, not a cursor-size change. "
                "The plan opens display settings and collects monitor, GPU, and plug-and-play evidence before proposing a fix."
            ),
            commands=[
                'cmd /c start "" ms-settings:display',
                'powershell -NoProfile -Command "Get-CimInstance Win32_DesktopMonitor"',
                'powershell -NoProfile -Command "Get-CimInstance Win32_VideoController"',
                'powershell -NoProfile -Command "Get-PnpDevice | Where-Object {$_.FriendlyName -match ''Display|Dock|USB|Monitor''}"',
            ],
            manual_steps=[
                "Identify the affected monitor in Windows display settings.",
                "Confirm rotation, scale, resolution, refresh rate, and dock connection path.",
                "Prepare a separate approved fix for any display setting, driver, or dock firmware change.",
            ],
            expected_effect="Collect evidence for the external monitor and dock path before changing display settings.",
            rollback=["No display setting is changed by the evidence commands; close Settings to stop here."],
            approval_prompt="Approve this evidence collection before any display setting or driver change is proposed.",
        )

    return _unsupported_platform_plan(request_text, platform_name, "display-dock")


DISPLAY_FIX_RE = re.compile(
    r"Output\s+(?P<output>[A-Za-z0-9_.:-]+)\.\s+"
    r"Set mode\s+(?P<width>\d+)x(?P<height>\d+)\s+refresh\s+(?P<refresh>[\d.]+)\s+"
    r"position\s+(?P<x>-?\d+),(?P<y>-?\d+)\s+scale\s+(?P<scale>[\d.]+)\s+"
    r"transform\s+(?P<transform>[A-Za-z0-9]+)\.\s+"
    r"Rollback mode\s+(?P<rollback_width>\d+)x(?P<rollback_height>\d+)\s+"
    r"refresh\s+(?P<rollback_refresh>[\d.]+)\s+"
    r"position\s+(?P<rollback_x>-?\d+),(?P<rollback_y>-?\d+)\s+"
    r"scale\s+(?P<rollback_scale>[\d.]+)\s+"
    r"transform\s+(?P<rollback_transform>[A-Za-z0-9]+)",
    re.IGNORECASE,
)
VALID_COSMIC_TRANSFORMS = {
    "normal",
    "rotate90",
    "rotate180",
    "rotate270",
    "flipped",
    "flipped90",
    "flipped180",
    "flipped270",
}


def _display_layout_fix_details(request_text: str) -> dict | None:
    match = DISPLAY_FIX_RE.search(request_text)
    if not match:
        return None
    details = match.groupdict()
    details["transform"] = details["transform"].lower()
    details["rollback_transform"] = details["rollback_transform"].lower()
    if details["transform"] not in VALID_COSMIC_TRANSFORMS:
        return None
    if details["rollback_transform"] not in VALID_COSMIC_TRANSFORMS:
        return None
    return details


def _cosmic_mode_command(details: dict, *, rollback: bool = False) -> str:
    prefix = "rollback_" if rollback else ""
    return (
        f"cosmic-randr mode {details['output']} "
        f"{details[prefix + 'width']} {details[prefix + 'height']} "
        f"--refresh {details[prefix + 'refresh']} "
        f"--pos-x {details[prefix + 'x']} --pos-y {details[prefix + 'y']} "
        f"--scale {details[prefix + 'scale']} "
        f"--transform {details[prefix + 'transform']}"
    )


def _cosmic_evidence_output(reasoning: dict | None) -> str:
    if not reasoning:
        return ""
    evidence = reasoning.get("request_evidence", {})
    for command in evidence.get("commands", []):
        if str(command.get("command", "")).startswith("cosmic-randr list"):
            return str(command.get("output", ""))
    return ""


def _display_layout_fix_plan(
    request_text: str,
    platform_name: str,
    platform_key: str,
    reasoning: dict | None = None,
) -> dict:
    details = _display_layout_fix_details(request_text)
    if platform_key == "linux" and not details:
        derived = build_cosmic_display_layout_request_from_intent(request_text, _cosmic_evidence_output(reasoning))
        if derived:
            request_text = derived["request_text"]
            details = _display_layout_fix_details(request_text)
            if reasoning is not None:
                reasoning["reasoning_summary"] = derived["summary"]
                reasoning["family"] = "display-layout-fix"
                reasoning["ready"] = True
    if platform_key != "linux" or not details:
        plan = _triage_plan(request_text, platform_name, "display-layout-fix")
        plan["summary"] = (
            "The request was identified as a display layout fix, but the app could not resolve an exact "
            "COSMIC output, mode, position, scale, transform, and rollback from the available evidence."
        )
        plan["expected_effect"] = "Wait for exact display evidence before changing a monitor layout."
        return plan

    command = _cosmic_mode_command(details)
    rollback_command = _cosmic_mode_command(details, rollback=True)
    return _request_plan(
        plan_id=f"request-display-layout-fix-{details['output'].lower()}",
        family="display-layout-fix",
        title=f"Apply COSMIC display layout fix to {details['output']}",
        request_text=request_text,
        platform_name=platform_name,
        risk="low",
        reversible=True,
        requires_privilege=False,
        summary=(
            f"Apply a current-user COSMIC display layout change for {details['output']}. "
            f"It sets {details['width']}x{details['height']} at {details['refresh']} Hz, "
            f"position {details['x']},{details['y']}, scale {details['scale']}, "
            f"and transform {details['transform']}."
        ),
        commands=[command, "cosmic-randr list"],
        manual_steps=[
            "Confirm the affected monitor is the named output before executing.",
            "After execution, confirm windows and cursor movement are usable on the target display.",
            "If the layout feels wrong, run the rollback command from this plan.",
        ],
        expected_effect="Change the target COSMIC display output layout without using privileged system commands.",
        rollback=[rollback_command],
        approval_prompt="Approve only when the named display output and rollback command match the evidence.",
    )


def _audio_plan(request_text: str, platform_name: str, platform_key: str) -> dict:
    input_request = _has_any(_normalize(request_text), ("microphone", "mic", "input"))
    target = "input" if input_request else "output"
    if platform_key == "linux":
        commands = ["pactl info", "pactl list short sinks", "pactl list short sources"]
    elif platform_key == "windows":
        commands = ["start ms-settings:sound", 'powershell -NoProfile -Command "Get-CimInstance Win32_SoundDevice"']
    else:
        return _unsupported_platform_plan(request_text, platform_name, "audio-routing")

    return _request_plan(
        plan_id=f"request-audio-{target}-{platform_key}",
        family="audio-routing",
        title=f"Plan an audio {target} change",
        request_text=request_text,
        platform_name=platform_name,
        risk="low",
        reversible=True,
        requires_privilege=False,
        summary="Prepare a user-session audio device or volume change after identifying active devices.",
        commands=commands,
        manual_steps=[
            f"Identify the current default audio {target} device.",
            "Test the target device in the operating-system sound settings.",
            "Change only one device or volume setting at a time.",
        ],
        expected_effect=f"Switch or tune the current user's audio {target} path without changing system-wide policy.",
        rollback=["Return to the sound settings page and select the previous device or volume level."],
        approval_prompt=f"Approve only after confirming the exact audio {target} device and previous value.",
    )


def _network_plan(request_text: str, platform_name: str, platform_key: str) -> dict:
    if platform_key == "linux":
        commands = ["ip route", "resolvectl status", "nmcli device status", "ping -c 4 1.1.1.1"]
    elif platform_key == "windows":
        commands = [
            "route print",
            "ipconfig /all",
            'powershell -NoProfile -Command "Resolve-DnsName example.com"',
            'powershell -NoProfile -Command "Test-NetConnection 1.1.1.1"',
        ]
    else:
        return _unsupported_platform_plan(request_text, platform_name, "network-dns")

    return _request_plan(
        plan_id=f"request-network-dns-{platform_key}",
        family="network-dns",
        title="Plan network and DNS troubleshooting",
        request_text=request_text,
        platform_name=platform_name,
        risk="low",
        reversible=True,
        requires_privilege=False,
        summary="Collect route, adapter, and DNS evidence before preparing any network configuration change.",
        commands=commands,
        manual_steps=[
            "Confirm whether the issue affects all apps or one app.",
            "Check route, DNS, adapter, VPN, and captive portal state.",
            "Prepare a separate approval plan before changing DNS servers, routes, adapters, or VPN settings.",
        ],
        expected_effect="Separate connectivity problems from DNS resolver problems before any fix is proposed.",
        rollback=["No setting change is proposed yet; rollback depends on the later approved network change."],
        approval_prompt="Approve only evidence collection until one adapter and one concrete network setting are identified.",
    )


def _package_plan(request_text: str, platform_name: str, platform_key: str) -> dict:
    if platform_key == "linux":
        commands = ["apt-get check", "dnf check", "pacman -Dk"]
    elif platform_key == "windows":
        commands = ["winget --info", "winget source list", "choco --version"]
    else:
        return _unsupported_platform_plan(request_text, platform_name, "package-updates")

    return _request_plan(
        plan_id=f"request-package-updates-{platform_key}",
        family="package-updates",
        title="Plan package and update repair",
        request_text=request_text,
        platform_name=platform_name,
        risk="medium",
        reversible=False,
        requires_privilege=True,
        summary="Review package manager health before approving install, remove, repair, upgrade, or source reset commands.",
        commands=commands,
        manual_steps=[
            "Identify the active package manager before running manager-specific commands.",
            "Review package database or source health output.",
            "Prepare a named package/source repair plan before any modifying command.",
        ],
        expected_effect="Identify package-manager health issues without modifying installed packages.",
        rollback=["No package change is proposed yet; rollback must be defined with the later approved repair command."],
        approval_prompt="Approve package changes only when exact packages, sources, and repair commands are visible.",
    )


def _pop_cosmic_plan(request_text: str, platform_name: str, platform_key: str) -> dict:
    if platform_key != "linux":
        return _unsupported_platform_plan(request_text, platform_name, "pop-cosmic")
    return _request_plan(
        plan_id="request-pop-cosmic-deep-scan-linux",
        family="pop-cosmic-deep-scan",
        title="Run Pop!_OS/COSMIC agent scan",
        request_text=request_text,
        platform_name=platform_name,
        risk="low",
        reversible=True,
        requires_privilege=False,
        summary=(
            "Collect bounded Pop!_OS/COSMIC evidence for the concern before proposing any package, firmware, "
            "session, display, or configuration fix."
        ),
        commands=[
            "pgrep -a cosmic",
            "systemctl --user --failed --no-legend --plain",
            "journalctl --user -b -n 300 --no-pager",
            "cosmic-randr list",
            "apt-get check",
            "apt list --upgradable",
        ],
        manual_steps=[
            "Review Pop!_OS/COSMIC profile, user services, display state, package health, and filtered UI logs.",
            "Use the Pop!_OS + COSMIC Agent page to run deeper analysis and build a ranked fix plan.",
            "Approve a separate exact fix only after scan evidence and rollback/verification are visible.",
        ],
        expected_effect="Collect Pop!_OS/COSMIC troubleshooting evidence without changing packages, services, settings, or display layout.",
        rollback=["No machine change is made by this evidence plan."],
        approval_prompt="Approve evidence collection only; this is not approval to update, repair packages, reset configs, restart the session, or install firmware.",
    )


def _docker_plan(request_text: str, platform_name: str, platform_key: str) -> dict:
    if platform_key not in {"linux", "windows"}:
        return _unsupported_platform_plan(request_text, platform_name, "docker-cleanup")

    return _request_plan(
        plan_id=f"request-docker-cleanup-{platform_key}",
        family="docker-cleanup",
        title="Plan Docker cleanup review",
        request_text=request_text,
        platform_name=platform_name,
        risk="medium",
        reversible=False,
        requires_privilege=False,
        summary="Inspect Docker disk usage and unused resources before approving any prune or delete command.",
        commands=["docker system df", "docker ps -a", "docker images", "docker volume ls"],
        manual_steps=[
            "Confirm whether stopped containers, unused images, build cache, or volumes are consuming space.",
            "Identify project-critical containers and volumes before cleanup.",
            "Prepare a separate approval plan for a specific prune/delete command.",
        ],
        expected_effect="Identify Docker cleanup candidates without deleting containers, images, caches, or volumes.",
        rollback=["Docker cleanup can be irreversible; define restore steps before approving any delete command."],
        approval_prompt="Approve cleanup only after naming the exact Docker resource class and preserving needed volumes.",
    )


def _startup_plan(request_text: str, platform_name: str, platform_key: str) -> dict:
    if platform_key == "linux":
        commands = ["systemctl --user list-unit-files --state=enabled", "ls ~/.config/autostart", "crontab -l"]
    elif platform_key == "windows":
        commands = [
            "start ms-settings:startupapps",
            'powershell -NoProfile -Command "Get-CimInstance Win32_StartupCommand | Select-Object Name,Command,Location"',
        ]
    else:
        return _unsupported_platform_plan(request_text, platform_name, "startup-apps")

    return _request_plan(
        plan_id=f"request-startup-apps-{platform_key}",
        family="startup-apps",
        title="Plan startup app review",
        request_text=request_text,
        platform_name=platform_name,
        risk="medium",
        reversible=True,
        requires_privilege=False,
        summary="List user-session startup entries before disabling anything.",
        commands=commands,
        manual_steps=[
            "Identify startup entries that are user-facing and nonessential.",
            "Disable one startup item at a time and reboot or sign out to confirm behavior.",
            "Keep security, sync, input, and driver utilities enabled unless their purpose is understood.",
        ],
        expected_effect="Identify candidate startup entries without disabling them.",
        rollback=["Re-enable the same startup item from the startup settings panel or user service list."],
        approval_prompt="Approve disabling only one named startup item at a time.",
    )


def _slow_computer_plan(request_text: str, platform_name: str, platform_key: str) -> dict:
    if platform_key == "linux":
        commands = ["uptime", "free -h", "df -h", "ps -eo pid,comm,%cpu,%mem --sort=-%cpu | head -20"]
    elif platform_key == "windows":
        commands = [
            'powershell -NoProfile -Command "Get-Process | Sort-Object CPU -Descending | Select-Object -First 15 Name,CPU,WorkingSet"',
            'powershell -NoProfile -Command "Get-CimInstance Win32_OperatingSystem | Select-Object FreePhysicalMemory,TotalVisibleMemorySize"',
            'powershell -NoProfile -Command "Get-PSDrive -PSProvider FileSystem"',
        ]
    else:
        return _unsupported_platform_plan(request_text, platform_name, "slow-computer")

    return _request_plan(
        plan_id=f"request-slow-computer-{platform_key}",
        family="slow-computer",
        title="Plan slow-computer triage",
        request_text=request_text,
        platform_name=platform_name,
        risk="low",
        reversible=True,
        requires_privilege=False,
        summary="Collect CPU, memory, disk, and process evidence before stopping apps, changing startup, or cleaning storage.",
        commands=commands,
        manual_steps=[
            "Capture whether the slowdown is constant, startup-only, app-specific, or network-related.",
            "Compare CPU, memory, disk space, and top process evidence.",
            "Turn the strongest evidence into a narrower approval-required plan.",
        ],
        expected_effect="Find the likely slowdown category without stopping processes or changing settings.",
        rollback=["No change is proposed yet; rollback depends on the later approved narrow plan."],
        approval_prompt="Approve only evidence collection until the slowdown has a clear category and target.",
    )


def _family_for_request(normalized: str, distribution_hint: str | None = None) -> str:
    if _is_display_dock_request(normalized):
        return "display-dock"
    if _has_any(normalized, ("cosmic display layout fix", "apply cosmic display layout fix")):
        return "display-layout-fix"
    if _linux_desktop_family(distribution_hint) == "cosmic" and _has_any(normalized, COSMIC_SHELL_TERMS):
        return "pop-cosmic"
    if _has_any(
        normalized,
        (
            "cosmic",
            "pop os",
            "pop!_os",
            "pop! os",
            "popos",
            "cosmic store",
            "cosmic panel",
            "cosmic launcher",
            "wayland",
            "xwayland",
            "compositor",
        ),
    ):
        return "pop-cosmic"
    if _has_any(normalized, ("cursor", "pointer")):
        return "cursor-size"
    if _has_any(normalized, ("docker", "container", "image", "volume", "prune")):
        return "docker-cleanup"
    if _has_any(normalized, ("startup", "start up", "login item", "autostart", "boot app")):
        return "startup-apps"
    if _has_any(normalized, ("network", "dns", "wifi", "wi-fi", "internet", "route", "gateway")):
        return "network-dns"
    if _has_any(normalized, ("package", "update", "upgrade", "apt", "dnf", "pacman", "winget", "choco")):
        return "package-updates"
    if _has_any(normalized, ("audio", "sound", "speaker", "microphone", "mic", "volume")):
        return "audio-routing"
    if _has_any(
        normalized,
        ("display", "monitor", "screen", "scale", "scaling", "brightness", "night light", "nightlight", "refresh", "hz"),
    ):
        return "display"
    if _has_any(normalized, ("slow", "sluggish", "lag", "laggy", "performance", "freezing", "hang")):
        return "slow-computer"
    return "unknown"


def review_request_intake(request_text: str, desktop_hint: str | None = None) -> dict:
    """Decide whether a request is ready for a plan or needs clarification."""

    normalized = _normalize(request_text)
    if not normalized:
        return {
            "ready": False,
            "family": "unknown",
            "acknowledgement": "I need a request before I can look into anything.",
            "questions": ["What setting, symptom, or maintenance issue should I inspect?"],
        }

    family = _family_for_request(normalized, desktop_hint)
    if family == "unknown":
        return {
            "ready": False,
            "family": family,
            "acknowledgement": "I do not have enough of a target yet.",
            "questions": [
                "What part of the computer is affected?",
                "What changed recently, if anything?",
                "Do you want investigation first, or do you already know the setting you want changed?",
            ],
        }

    if family == "cursor-size":
        direction = _cursor_direction(normalized)
        wants_investigation = _has_any(normalized, ("investigate", "look into", "check", "jitter", "jittery", "loses", "lost", "disappear"))
        if direction == "adjust" and not wants_investigation:
            return {
                "ready": False,
                "family": family,
                "acknowledgement": "I can help with the pointer, but I need the direction before I change it.",
                "questions": [
                    "Do you want the cursor smaller, larger, easier to find, or do you want me to investigate pointer behavior first?",
                    "Does this happen everywhere, or only while dragging windows or using a specific app?",
                ],
            }
        if wants_investigation and direction == "adjust":
            return {
                "ready": True,
                "family": family,
                "acknowledgement": "I will start by checking safe pointer settings and then we can narrow the jitter or disappearing-cursor symptom from there.",
                "questions": [],
            }

    if family == "display-dock":
        return {
            "ready": True,
            "family": family,
            "acknowledgement": (
                "That sounds like a display, dock, and compositor path issue, not a cursor-size setting. "
                "I will collect monitor layout, rotation, dock, GPU, and recent session log evidence before proposing a fix."
            ),
            "questions": [],
        }

    if family == "audio-routing" and not _has_any(normalized, ("output", "speaker", "speakers", "input", "microphone", "mic", "volume")):
        return {
            "ready": False,
            "family": family,
            "acknowledgement": "Audio can mean output, microphone input, device routing, or volume.",
            "questions": ["Is the problem with speakers/output, microphone/input, or volume level?"],
        }

    if family == "display" and not _has_any(normalized, ("brightness", "scale", "scaling", "night", "refresh", "hz", "monitor", "screen")):
        return {
            "ready": False,
            "family": family,
            "acknowledgement": "Display is a broad area, so I need one more detail.",
            "questions": ["Is the issue brightness, scaling/text size, night light/color, refresh rate, or the active monitor?"],
        }

    return {
        "ready": True,
        "family": family,
        "acknowledgement": "Okay, I have enough to prepare a guarded plan. I will show exactly what I found and what I would run before anything executes.",
        "questions": [],
    }


def _apply_reasoning_metadata(plan: dict, reasoning: dict | None) -> dict:
    if reasoning:
        plan["reasoning_brain"] = {
            "source": reasoning.get("source", "deterministic"),
            "model": reasoning.get("model"),
            "family": reasoning.get("family"),
            "ready": reasoning.get("ready"),
            "confidence": reasoning.get("confidence"),
            "summary": reasoning.get("reasoning_summary", ""),
            "evidence_assessment": reasoning.get("evidence_assessment", ""),
            "alternate_families": reasoning.get("alternate_families", []),
            "investigation_steps": reasoning.get("investigation_steps", []),
            "permission_plan": reasoning.get("permission_plan", ""),
            "evidence_scopes": reasoning.get("request_evidence", {}).get("scopes", []),
            "evidence_command_count": len(reasoning.get("request_evidence", {}).get("commands", [])),
        }
    else:
        plan["reasoning_brain"] = {
            "source": "deterministic",
            "model": None,
            "family": plan.get("family"),
            "ready": True,
            "confidence": None,
            "summary": "Prepared by deterministic request rules.",
            "evidence_assessment": "",
            "alternate_families": [],
            "investigation_steps": [],
            "permission_plan": "",
            "evidence_scopes": [],
            "evidence_command_count": 0,
        }
    return plan


def prepare_request_plan(
    request_text: str,
    os_name: str | None = None,
    distribution_hint: str | None = None,
    family_override: str | None = None,
    reasoning: dict | None = None,
) -> dict:
    """Turn a user maintenance request into an approval-required plan preview."""

    resolved_os = os_name or platform.system() or "Unknown"
    platform_key = _platform_key(resolved_os)
    platform_name = _platform_label(platform_key, resolved_os)
    normalized = _normalize(request_text)
    if not normalized:
        return _apply_reasoning_metadata(_triage_plan(request_text, platform_name), reasoning)

    requested_family = (family_override or "").strip()
    family = requested_family if requested_family in SUPPORTED_FAMILY_OVERRIDES else _family_for_request(normalized, distribution_hint)
    if family == "unknown":
        return _apply_reasoning_metadata(_triage_plan(request_text, platform_name), reasoning)
    if family == "display-dock":
        return _apply_reasoning_metadata(_display_dock_plan(request_text, platform_name, platform_key, distribution_hint), reasoning)
    if family == "display-layout-fix":
        return _apply_reasoning_metadata(_display_layout_fix_plan(request_text, platform_name, platform_key, reasoning), reasoning)
    if family == "cursor-size":
        return _apply_reasoning_metadata(_cursor_plan(request_text, platform_name, platform_key, distribution_hint), reasoning)
    if family == "display":
        return _apply_reasoning_metadata(_display_plan(request_text, platform_name, platform_key), reasoning)
    if family == "audio-routing":
        return _apply_reasoning_metadata(_audio_plan(request_text, platform_name, platform_key), reasoning)
    if family == "network-dns":
        return _apply_reasoning_metadata(_network_plan(request_text, platform_name, platform_key), reasoning)
    if family == "package-updates":
        return _apply_reasoning_metadata(_package_plan(request_text, platform_name, platform_key), reasoning)
    if family == "pop-cosmic":
        return _apply_reasoning_metadata(_pop_cosmic_plan(request_text, platform_name, platform_key), reasoning)
    if family == "docker-cleanup":
        return _apply_reasoning_metadata(_docker_plan(request_text, platform_name, platform_key), reasoning)
    if family == "startup-apps":
        return _apply_reasoning_metadata(_startup_plan(request_text, platform_name, platform_key), reasoning)
    if family == "slow-computer":
        return _apply_reasoning_metadata(_slow_computer_plan(request_text, platform_name, platform_key), reasoning)
    return _apply_reasoning_metadata(_triage_plan(request_text, platform_name), reasoning)


def format_request_plan(plan: dict) -> str:
    lines = [
        plan["title"],
        f"Family: {plan.get('family', 'unknown')}",
        f"Platform: {plan['platform']}",
        f"Risk: {plan['risk']}",
        f"Requires privilege: {plan['requires_privilege']}",
        f"Reversible: {plan['reversible']}",
        f"Approval required: {plan['approval_required']}",
        f"Execution enabled: {plan['execution_enabled']}",
        f"Reasoning brain: {plan.get('reasoning_brain', {}).get('source', 'deterministic')}"
        + (
            f" ({plan.get('reasoning_brain', {}).get('model')})"
            if plan.get("reasoning_brain", {}).get("model")
            else ""
        ),
        f"Evidence scopes: {', '.join(plan.get('reasoning_brain', {}).get('evidence_scopes', [])) or 'none'}",
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
