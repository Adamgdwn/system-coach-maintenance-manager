"""Transforms raw agent findings into learner-friendly reports."""

from __future__ import annotations

from collections import Counter
import datetime as dt

from .knowledge import STACK_PATTERNS, describe_component


def _normalize_tool(probe: dict) -> dict | None:
    if not probe.get("installed"):
        return None

    command_name = probe["command"]

    info = describe_component(command_name)
    return {
        "command": command_name,
        "label": info["label"],
        "category": info["category"],
        "version": probe.get("version"),
        "path": probe.get("path"),
        "role": info["role"],
        "pairs_well_with": info["pairs_well_with"],
        "learning_tip": info["learning_tip"],
    }


def _build_stack_matches(installed_commands: set[str]) -> list[dict]:
    matches = []
    for pattern in STACK_PATTERNS:
        if not pattern["requires"].issubset(installed_commands):
            continue
        signal_count = len(pattern["signals"].intersection(installed_commands))
        confidence = "high" if signal_count >= 2 else "medium"
        matches.append(
            {
                "title": pattern["title"],
                "summary": pattern["summary"],
                "coaching": pattern["coaching"],
                "confidence": confidence,
            }
        )
    return matches


def _build_recommendations(installed_commands: set[str]) -> list[str]:
    recommendations = []
    if "python3" in installed_commands and "venv" not in installed_commands:
        recommendations.append(
            "Python is installed. If you are learning Python projects, add `python3 -m venv .venv` to your toolkit so dependencies stay isolated."
        )
    if "node" in installed_commands and "npm" not in installed_commands and "pnpm" not in installed_commands:
        recommendations.append(
            "Node.js is present, but no JavaScript package manager was detected. Most Node projects expect `npm` or `pnpm`."
        )
    if "docker" in installed_commands and "git" in installed_commands:
        recommendations.append(
            "Docker plus Git is a strong combo for reproducible development. Look for `Dockerfile` and compose files in projects to see how services are assembled."
        )
    if "inkscape" in installed_commands and (
        {"gimp", "krita", "convert", "magick", "chromium", "ffmpeg"} & installed_commands
    ):
        recommendations.append(
            "This machine includes a creative production toolkit. You can combine vector design, raster effects, browser rendering, and export tooling to build polished visuals and shareable client assets."
        )
    if "playwright" in installed_commands and "chromium" in installed_commands:
        recommendations.append(
            "Playwright plus Chromium means the machine can automate screenshots, PDF export, and repeatable visual checks. That is useful when you want designs or demo pages rendered consistently."
        )
    if "flatpak" in installed_commands and ({"gimp", "krita"} & installed_commands):
        recommendations.append(
            "Some design apps are installed through Flatpak. That is normal for desktop tools, but scanners and scripts may need to account for app IDs instead of assuming a plain shell command exists."
        )
    if "git" not in installed_commands:
        recommendations.append(
            "Git was not detected. Installing Git is one of the highest-leverage steps for learning and collaborating in modern codebases."
        )
    if not recommendations:
        recommendations.append(
            "This environment already has several core development tools installed. Try opening a project and compare its files to the tool list here to understand how the stack fits together."
        )
    return recommendations


def generate_report(agent_results: list[dict]) -> dict:
    environment = next(result for result in agent_results if result["id"] == "environment")

    components = []
    command_log = []
    for result in agent_results:
        command_log.extend(result.get("commands", []))
        findings = result.get("findings", [])
        if isinstance(findings, list):
            for probe in findings:
                normalized = _normalize_tool(probe)
                if normalized:
                    components.append(normalized)

    deduped = {}
    for component in components:
        deduped[component["command"]] = component
    components = sorted(deduped.values(), key=lambda item: (item["category"], item["label"].lower()))

    installed_commands = {component["command"] for component in components}
    categories = Counter(component["category"] for component in components)

    learning_path = [
        "Start with the environment panel to learn what operating system, shell, and session type you are working inside.",
        "Move to installed components and focus first on languages, package managers, source control, and containers.",
        "Use the compatibility notes to see which tools usually appear together in real projects.",
        "Open a project repository afterward and compare its files to this report so the stack becomes concrete.",
    ]

    return {
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "environment": environment["findings"],
        "summary": {
            "installed_component_count": len(components),
            "category_breakdown": dict(categories),
            "primary_stack_matches": _build_stack_matches(installed_commands),
        },
        "components": components,
        "recommendations": _build_recommendations(installed_commands),
        "learning_path": learning_path,
        "command_log": command_log,
    }
