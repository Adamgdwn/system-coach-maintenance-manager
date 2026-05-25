"""Turn executed evidence into the next guarded request plan."""

from __future__ import annotations

from collections import Counter
import re
from typing import Any


ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
DISPLAY_HEADER_RE = re.compile(r"^(?P<name>[A-Za-z0-9_.:-]+)\s+\(enabled\)")
POSITION_RE = re.compile(r"Position:\s*(-?\d+),(-?\d+)")
SCALE_RE = re.compile(r"Scale:\s*(\d+(?:\.\d+)?)%")
TRANSFORM_RE = re.compile(r"Transform:\s*([A-Za-z0-9]+)")
MODEL_RE = re.compile(r"Model:\s*(.*)")
CURRENT_MODE_RE = re.compile(r"(\d+)\s*x\s*(\d+)\s*@\s*([\d.]+)\s*Hz.*\(current\)")
OUTPUT_NAME_RE = re.compile(r"\b(?:eDP|DVI-I|DP|HDMI|VGA)-[A-Za-z0-9_.:-]+\b", re.IGNORECASE)
COSMIC_PANEL_BUTTON_RE = re.compile(r"\bcosmic-panel-button\s+(com\.system76\.[A-Za-z0-9]+)")
COSMIC_PANEL_BROKEN_PIPE_RE = re.compile(r"cosmic-panel.*broken pipe", re.IGNORECASE)
COSMIC_APPLET_EXIT_RE = re.compile(r"cosmic-panel.*Cosmic(?:Applet|Panel|AppList).*exited with code", re.IGNORECASE)


def _strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


def _scale_percent_to_ratio(value: float) -> str:
    ratio = value / 100
    return f"{ratio:.2f}".rstrip("0").rstrip(".")


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _refresh_value(value: str) -> str:
    try:
        number = float(value)
    except ValueError:
        return value
    if number.is_integer():
        return str(int(number))
    return f"{number:.3f}".rstrip("0").rstrip(".")


def parse_cosmic_displays(output: str) -> list[dict[str, Any]]:
    """Parse the stable parts of `cosmic-randr list` output."""

    displays: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for raw_line in _strip_ansi(output).splitlines():
        line = raw_line.rstrip()
        header = DISPLAY_HEADER_RE.match(line.strip())
        if header:
            current = {"name": header.group("name"), "current_mode": None}
            displays.append(current)
            continue
        if not current:
            continue

        stripped = line.strip()
        if match := MODEL_RE.match(stripped):
            model = match.group(1).strip()
            if model:
                current["model"] = model
        elif match := POSITION_RE.match(stripped):
            current["x"] = int(match.group(1))
            current["y"] = int(match.group(2))
        elif match := SCALE_RE.match(stripped):
            current["scale_percent"] = float(match.group(1))
        elif match := TRANSFORM_RE.match(stripped):
            current["transform"] = match.group(1)
        elif match := CURRENT_MODE_RE.search(stripped):
            current["current_mode"] = {
                "width": int(match.group(1)),
                "height": int(match.group(2)),
                "refresh": _refresh_value(match.group(3)),
            }
    return displays


def _choose_affected_display(displays: list[dict[str, Any]]) -> dict[str, Any] | None:
    rotated = [item for item in displays if item.get("transform") and item.get("transform") != "normal"]
    if rotated:
        return sorted(rotated, key=lambda item: item.get("x", 0), reverse=True)[0]
    external = [item for item in displays if not item.get("name", "").startswith("eDP-")]
    if not external:
        return None
    scales = [
        item.get("scale_percent")
        for item in external
        if item.get("scale_percent") is not None and item.get("transform", "normal") == "normal"
    ]
    if not scales:
        return None
    common_scale = Counter(scales).most_common(1)[0][0]
    scaled = [item for item in external if item.get("scale_percent") is not None and item.get("scale_percent") != common_scale]
    if scaled:
        return sorted(scaled, key=lambda item: item.get("x", 0), reverse=True)[0]
    return None


def _common_external_y(displays: list[dict[str, Any]], affected: dict[str, Any]) -> int | None:
    external_y = [
        item["y"]
        for item in displays
        if item is not affected
        and not item.get("name", "").startswith("eDP-")
        and item.get("transform", "normal") == "normal"
        and "y" in item
    ]
    if not external_y:
        return affected.get("y")
    return Counter(external_y).most_common(1)[0][0]


def _target_transform_from_request(request_text: str) -> str | None:
    normalized = _normalize(request_text)
    if "normal" in normalized or "landscape" in normalized or "unrotate" in normalized:
        return "normal"
    if "180" in normalized:
        return "rotate180"
    if "270" in normalized:
        return "rotate270"
    if "90" in normalized or "portrait" in normalized or "rotate" in normalized or "rotated" in normalized:
        return "rotate90"
    return None


def _choose_display_from_request(displays: list[dict[str, Any]], request_text: str) -> dict[str, Any] | None:
    normalized = _normalize(request_text)
    named = OUTPUT_NAME_RE.search(request_text)
    if named:
        output = named.group(0).lower()
        for display in displays:
            if display.get("name", "").lower() == output:
                return display

    external = [item for item in displays if not item.get("name", "").startswith("eDP-")]
    candidates = external or displays
    if not candidates:
        return None
    if "right" in normalized or "far right" in normalized:
        return sorted(candidates, key=lambda item: item.get("x", 0), reverse=True)[0]
    if "left" in normalized:
        return sorted(candidates, key=lambda item: item.get("x", 0))[0]
    return _choose_affected_display(displays) or sorted(candidates, key=lambda item: item.get("x", 0), reverse=True)[0]


def build_cosmic_display_layout_request_from_intent(request_text: str, output: str) -> dict[str, Any] | None:
    """Resolve a plain-language display request into an exact COSMIC layout request."""

    transform = _target_transform_from_request(request_text)
    if not transform:
        return None
    displays = parse_cosmic_displays(output)
    target = _choose_display_from_request(displays, request_text)
    if not target or not target.get("current_mode"):
        return None
    if not {"x", "y", "scale_percent", "transform"} <= target.keys():
        return None

    mode = target["current_mode"]
    target_y = target.get("y")
    if transform == "normal":
        target_y = _common_external_y(displays, target)
    if target_y is None:
        target_y = 0

    old_scale = _scale_percent_to_ratio(float(target["scale_percent"]))
    request = (
        "Apply COSMIC display layout fix. "
        f"Output {target['name']}. "
        f"Set mode {mode['width']}x{mode['height']} refresh {mode['refresh']} "
        f"position {target['x']},{target_y} scale 1.0 transform {transform}. "
        f"Rollback mode {mode['width']}x{mode['height']} refresh {mode['refresh']} "
        f"position {target['x']},{target['y']} scale {old_scale} transform {target['transform']}."
    )
    model = target.get("model")
    return {
        "family": "display-layout-fix",
        "request_text": request,
        "summary": (
            f"Resolved the plain-language request to {target['name']}"
            + (f" ({model})" if model else "")
            + f": set transform {transform}, scale 100%, position {target['x']},{target_y}."
        ),
        "target_output": target["name"],
    }


def derive_cosmic_display_layout_fix(output: str) -> dict[str, Any] | None:
    """Create an executable COSMIC layout fix from display evidence."""

    displays = parse_cosmic_displays(output)
    affected = _choose_affected_display(displays)
    if not affected or not affected.get("current_mode"):
        return None
    if not {"x", "y", "scale_percent", "transform"} <= affected.keys():
        return None

    mode = affected["current_mode"]
    target_y = _common_external_y(displays, affected)
    if target_y is None:
        return None

    old_scale = _scale_percent_to_ratio(float(affected["scale_percent"]))
    request_text = (
        "Apply COSMIC display layout fix. "
        f"Output {affected['name']}. "
        f"Set mode {mode['width']}x{mode['height']} refresh {mode['refresh']} "
        f"position {affected['x']},{target_y} scale 1.0 transform normal. "
        f"Rollback mode {mode['width']}x{mode['height']} refresh {mode['refresh']} "
        f"position {affected['x']},{affected['y']} scale {old_scale} transform {affected['transform']}."
    )
    model = affected.get("model")
    summary = (
        f"{affected['name']}"
        + (f" ({model})" if model else "")
        + f" is using transform {affected['transform']} at {int(affected['scale_percent'])}% scale. "
        f"The proposed fix sets it back to normal rotation, 100% scale, and aligns it at y={target_y}."
    )
    return {
        "family": "display-layout-fix",
        "request_text": request_text,
        "summary": summary,
        "target_output": affected["name"],
    }


def _summarize_cosmic_panel_evidence(output: str) -> dict[str, Any]:
    clean_output = _strip_ansi(output)
    panel_buttons = COSMIC_PANEL_BUTTON_RE.findall(clean_output)
    button_counts = Counter(panel_buttons)
    duplicated_buttons = {name: count for name, count in button_counts.items() if count > 1}
    broken_pipe_lines = [line.strip() for line in clean_output.splitlines() if COSMIC_PANEL_BROKEN_PIPE_RE.search(line)]
    applet_exit_lines = [line.strip() for line in clean_output.splitlines() if COSMIC_APPLET_EXIT_RE.search(line)]
    panel_process_lines = [line.strip() for line in clean_output.splitlines() if " cosmic-panel" in line or line.endswith("cosmic-panel")]
    return {
        "button_counts": dict(button_counts),
        "duplicated_buttons": duplicated_buttons,
        "broken_pipe_count": len(broken_pipe_lines),
        "broken_pipe_sample": broken_pipe_lines[:3],
        "applet_exit_count": len(applet_exit_lines),
        "applet_exit_sample": applet_exit_lines[:3],
        "panel_process_count": len(panel_process_lines),
    }


def derive_cosmic_panel_restart_fix(request_text: str, output: str) -> dict[str, Any] | None:
    """Create a targeted panel restart request from COSMIC shell evidence."""

    normalized = _normalize(request_text)
    shell_terms = ("bottom bar", "panel", "launcher", "icon", "icons", "applet", "workspaces", "app library")
    if not any(term in normalized for term in shell_terms):
        return None
    evidence = _summarize_cosmic_panel_evidence(output)
    if not (evidence["duplicated_buttons"] or evidence["broken_pipe_count"] or evidence["applet_exit_count"]):
        return None

    observed = []
    if evidence["duplicated_buttons"]:
        duplicates = ", ".join(f"{name} x{count}" for name, count in sorted(evidence["duplicated_buttons"].items()))
        observed.append(f"duplicated COSMIC panel-button processes ({duplicates})")
    if evidence["broken_pipe_count"]:
        observed.append(f"{evidence['broken_pipe_count']} recent cosmic-panel broken-pipe log line(s)")
    if evidence["applet_exit_count"]:
        observed.append(f"{evidence['applet_exit_count']} recent COSMIC panel/applet exit line(s)")

    summary = (
        "Evidence points to stale COSMIC panel state rather than a pointer setting: "
        + "; ".join(observed)
        + ". The narrow next fix is to restart only the current user's cosmic-panel process and then retest the left-side bottom-bar icons."
    )
    return {
        "family": "pop-cosmic-panel-restart",
        "request_text": "Restart the current-user COSMIC panel because bottom-bar icon evidence points to stale panel state.",
        "summary": summary,
        "evidence": evidence,
    }


def build_followup_request(plan: dict, result: dict, analysis: dict | None = None) -> dict[str, Any] | None:
    """Return the next request to prepare after a successful evidence action."""

    if result.get("status") != "completed":
        return None
    family = plan.get("family")
    if family == "display-dock":
        followup = derive_cosmic_display_layout_fix(str(result.get("output", "")))
        if not followup:
            return None
        followup["reasoning"] = {
            "source": "deterministic-followup",
            "model": (analysis or {}).get("model"),
            "family": followup["family"],
            "ready": True,
            "confidence": 0.9,
            "reasoning_summary": followup["summary"],
            "request_evidence": {
                "scopes": ["display-dock", "display-layout-fix"],
                "commands": [{"command": command, "output": ""} for command in result.get("commands", [])],
            },
        }
        return followup
    if family == "pop-cosmic-deep-scan":
        followup = derive_cosmic_panel_restart_fix(str(plan.get("request", "")), str(result.get("output", "")))
        if not followup:
            return None
        followup["reasoning"] = {
            "source": "deterministic-followup",
            "model": (analysis or {}).get("model"),
            "family": followup["family"],
            "ready": True,
            "confidence": 0.85,
            "reasoning_summary": followup["summary"],
            "evidence_assessment": "The evidence scan found COSMIC panel/app-button state that matches the reported unselectable bottom-bar icons.",
            "investigation_steps": [
                "Restart only the current user's cosmic-panel process.",
                "Retest the left-side bottom-bar icons after the panel returns.",
                "If the problem remains, collect a fresh panel log sample and escalate to a COSMIC session investigation.",
            ],
            "permission_plan": (
                "This is a current-user action that restarts only the current user's cosmic-panel process. "
                "It does not need administrator privileges, but still requires explicit approval."
            ),
            "request_evidence": {
                "scopes": ["pop-cosmic", "cosmic-panel"],
                "commands": [{"command": command, "output": ""} for command in result.get("commands", [])],
            },
        }
        return followup
    return None
