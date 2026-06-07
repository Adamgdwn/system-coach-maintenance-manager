"""Autonomy and depth control settings for the agent execution gate."""

from __future__ import annotations

from pathlib import Path

_AUTONOMY_LEVELS = ("A0", "A1", "A2", "A3", "A4")
_EXECUTABLE_LEVELS = {"A1", "A2", "A3", "A4"}

# tier → minimum autonomy level index required for auto-execution (no explicit click)
# A2 auto-fires low-risk; A3 auto-fires low+medium; A4 auto-fires all
_AUTO_EXECUTE_THRESHOLD: dict[str, int] = {
    "low": _AUTONOMY_LEVELS.index("A2"),
    "medium": _AUTONOMY_LEVELS.index("A3"),
    "high": _AUTONOMY_LEVELS.index("A4"),
}

_DEPTH_LEVELS = ("D1", "D2", "D3", "D4")


def _load_raw(project_control_path: Path | None = None) -> dict[str, str]:
    path = project_control_path or Path.cwd() / "project-control.yaml"
    raw: dict[str, str] = {}
    if not path.exists():
        return raw
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("agent_autonomy_level:"):
            raw["autonomy"] = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("agent_depth_level:"):
            raw["depth"] = stripped.split(":", 1)[1].strip()
    return raw


def load_autonomy_settings(project_control_path: Path | None = None) -> dict:
    """Return the current autonomy and depth settings as a plain dict."""
    raw = _load_raw(project_control_path)
    autonomy = raw.get("autonomy", "A0")
    depth = raw.get("depth", "D1")
    return {
        "agent_autonomy_level": autonomy if autonomy in _AUTONOMY_LEVELS else "A0",
        "agent_depth_level": depth if depth in _DEPTH_LEVELS else "D1",
    }


def execution_allowed(project_control_path: Path | None = None) -> bool:
    """Return True if the current autonomy level permits action execution (A1+)."""
    settings = load_autonomy_settings(project_control_path)
    return settings["agent_autonomy_level"] in _EXECUTABLE_LEVELS


def can_auto_execute(tier: str, project_control_path: Path | None = None) -> bool:
    """Return True if the current autonomy level auto-fires for the given risk tier.

    Auto-execute means the action fires without an explicit user click:
      A2 → auto-fires low-risk (countdown, cancelable)
      A3 → auto-fires low and medium risk
      A4 → auto-fires all tiers
    A0 and A1 always return False.
    """
    settings = load_autonomy_settings(project_control_path)
    level = settings["agent_autonomy_level"]
    if level not in _AUTONOMY_LEVELS:
        return False
    level_index = _AUTONOMY_LEVELS.index(level)
    threshold = _AUTO_EXECUTE_THRESHOLD.get(tier.lower(), len(_AUTONOMY_LEVELS))
    return level_index >= threshold


def max_depth(project_control_path: Path | None = None) -> int:
    """Return the configured depth level as an integer (1–4)."""
    settings = load_autonomy_settings(project_control_path)
    level = settings["agent_depth_level"]
    if level in _DEPTH_LEVELS:
        return _DEPTH_LEVELS.index(level) + 1
    return 1
