"""Project-control readers for the Pop!_OS/COSMIC agent."""

from __future__ import annotations

from pathlib import Path


DEFAULT_ALLOWED_DOMAINS = [
    "system76.com",
    "support.system76.com",
    "blog.system76.com",
    "github.com/pop-os",
    "api.github.com/repos/pop-os",
    "api.github.com/search/issues",
    "ai.google.dev",
    "deepmind.google",
    "ollama.com",
]


def _parse_bool(value: str) -> bool:
    return value.strip().lower() in {"true", "yes", "1", "on"}


def _parse_int(value: str, fallback: int) -> int:
    try:
        return int(value.strip())
    except ValueError:
        return fallback


def load_pop_cosmic_controls(project_control_path: Path | None = None) -> dict:
    """Load the narrow Pop/COSMIC governance controls needed by local API endpoints."""

    path = project_control_path or Path.cwd() / "project-control.yaml"
    controls = {
        "source": str(path),
        "web_research_enabled": False,
        "allowed_domains": list(DEFAULT_ALLOWED_DOMAINS),
        "searxng_url": "",
        "research_provider": "official",
        "perplexity_api_key_env_var": "PERPLEXITY_API_KEY",
        "perplexity_model_env_var": "PERPLEXITY_MODEL",
        "master_env_path": "",
        "max_results_per_query": 8,
        "cache_ttl_days": 14,
        "mode": "guided-fix",
        "loaded": False,
        "governance_reason": "Pop/COSMIC web research is disabled by default unless project-control.yaml enables it.",
    }
    if not path.exists():
        controls["governance_reason"] = "project-control.yaml was not found, so live Pop/COSMIC web research is disabled."
        return controls

    in_section = False
    in_allowed_domains = False
    allowed_domains: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        is_top_level = raw_line == raw_line.lstrip()
        stripped = raw_line.strip()
        if is_top_level:
            in_section = stripped == "pop_cosmic_agent:"
            in_allowed_domains = False
            continue
        if not in_section:
            continue
        if stripped.startswith("allowed_domains:"):
            in_allowed_domains = True
            continue
        if in_allowed_domains and stripped.startswith("- "):
            allowed_domains.append(stripped[2:].strip().strip('"'))
            continue
        in_allowed_domains = False
        if ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        value = value.strip().strip('"')
        if key == "web_research_enabled":
            controls["web_research_enabled"] = _parse_bool(value)
        elif key == "searxng_url":
            controls["searxng_url"] = value
        elif key == "research_provider":
            controls["research_provider"] = value or "official"
        elif key == "perplexity_api_key_env_var":
            controls["perplexity_api_key_env_var"] = value or "PERPLEXITY_API_KEY"
        elif key == "perplexity_model_env_var":
            controls["perplexity_model_env_var"] = value or "PERPLEXITY_MODEL"
        elif key == "master_env_path":
            controls["master_env_path"] = value
        elif key == "max_results_per_query":
            controls["max_results_per_query"] = _parse_int(value, 8)
        elif key == "cache_ttl_days":
            controls["cache_ttl_days"] = _parse_int(value, 14)
        elif key == "mode":
            controls["mode"] = value or "guided-fix"

    if allowed_domains:
        controls["allowed_domains"] = allowed_domains
    controls["loaded"] = True
    if controls["web_research_enabled"]:
        controls["governance_reason"] = (
            f"Project controls allow live Pop/COSMIC web research through {controls['research_provider']} "
            "when the request also opts in."
        )
    return controls
