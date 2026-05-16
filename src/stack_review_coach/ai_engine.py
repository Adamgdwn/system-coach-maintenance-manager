"""Local AI coaching engine backed by Ollama."""

from __future__ import annotations

import json
from typing import Any
import urllib.error
import urllib.request


OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_TIMEOUT = 45
PREFERRED_MODELS = ["gemma4:latest", "gemma4", "gemma4:e4b", "qwen3:8b", "qwen3", "llama3.1:8b", "mistral"]


def _post_json(path: str, payload: dict[str, Any], timeout: int = DEFAULT_TIMEOUT) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{OLLAMA_URL}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def _get_json(path: str, timeout: int = 5) -> dict[str, Any]:
    with urllib.request.urlopen(f"{OLLAMA_URL}{path}", timeout=timeout) as response:
        return json.load(response)


def get_engine_status() -> dict[str, Any]:
    try:
        data = _get_json("/api/tags")
    except urllib.error.URLError as exc:
        return {
            "available": False,
            "provider": "ollama",
            "models": [],
            "selected_model": None,
            "message": f"Ollama is not reachable on {OLLAMA_URL}: {exc.reason}",
        }

    models = [item["name"] for item in data.get("models", [])]
    selected_model = choose_model(models)
    if not selected_model:
        return {
            "available": False,
            "provider": "ollama",
            "models": models,
            "selected_model": None,
            "message": "Ollama is running, but no supported local model was found.",
        }

    return {
        "available": True,
        "provider": "ollama",
        "models": models,
        "selected_model": selected_model,
        "message": f"Using local model {selected_model} through Ollama.",
    }


def choose_model(models: list[str]) -> str | None:
    if not models:
        return None
    for preferred in PREFERRED_MODELS:
        if preferred in models:
            return preferred
    return models[0]


def build_context(
    report: dict | None,
    system_map: dict | None = None,
    maintenance_report: dict | None = None,
    request_plan: dict | None = None,
) -> str:
    if not report:
        return "No system report is available yet. Ask the user to run a local review first."

    lines = [
        "You are a local desktop coaching assistant for a system stack learning app.",
        "Answer clearly for a new to intermediate coder.",
        "Prefer practical, general explanations over deep theory.",
        "Base your answer on the local report and map below.",
        "If something is unknown, say so instead of guessing.",
        "",
        "Environment:",
    ]
    lines.extend(f"- {key}: {value}" for key, value in report["environment"].items())
    lines.extend(
        [
            "",
            "Installed components:",
            *[
                f"- {component['label']} [{component['category']}] version={component['version']} path={component['path']}"
                for component in report["components"][:30]
            ],
            "",
            "Likely stack patterns:",
            *[
                f"- {item['title']} ({item['confidence']}): {item['summary']} | {item['coaching']}"
                for item in report["summary"]["primary_stack_matches"]
            ],
            "",
            "Recommendations:",
            *[f"- {item}" for item in report["recommendations"]],
        ]
    )

    if system_map:
        lines.extend(
            [
                "",
                "Filesystem map summary:",
                *[f"- {key}: {value}" for key, value in system_map["summary"].items()],
                "",
                "Scanned roots:",
                *[f"- {root}" for root in system_map["requested_roots"]],
                "",
                "Detected projects:",
            ]
        )
        for scan in system_map.get("scans", []):
            for project in scan.get("projects", [])[:20]:
                lines.append(f"- {project['path']} => {', '.join(project['types'])}")
        if system_map.get("config_findings"):
            lines.extend(["", "Config findings:"])
            lines.extend(f"- {item['label']}: {item['path']}" for item in system_map["config_findings"][:20])

    if maintenance_report:
        lines.extend(
            [
                "",
                "Maintenance diagnostics summary:",
                *[f"- {key}: {value}" for key, value in maintenance_report["summary"].items()],
                "",
                "Maintenance findings:",
            ]
        )
        for finding in maintenance_report.get("findings", [])[:12]:
            lines.append(
                f"- {finding['title']} [{finding['severity']}]: {finding['summary']} "
                f"| next: {'; '.join(finding['recommended_next_steps'][:2])}"
            )
        if maintenance_report.get("action_plans"):
            lines.extend(["", "Approval-required maintenance plans:"])
            for plan in maintenance_report["action_plans"][:8]:
                lines.append(
                    f"- {plan['title']} risk={plan['risk']} privilege={plan['requires_privilege']} "
                    f"execution_enabled={plan['execution_enabled']}"
                )
    if request_plan:
        lines.extend(
            [
                "",
                "Latest user-requested approval plan:",
                f"- title: {request_plan['title']}",
                f"- platform: {request_plan['platform']}",
                f"- risk: {request_plan['risk']}",
                f"- requires_privilege: {request_plan['requires_privilege']}",
                f"- execution_enabled: {request_plan['execution_enabled']}",
                f"- approval_prompt: {request_plan['approval_prompt']}",
            ]
        )
    return "\n".join(lines)


def answer_question(
    question: str,
    report: dict | None,
    system_map: dict | None = None,
    maintenance_report: dict | None = None,
    request_plan: dict | None = None,
) -> dict[str, Any]:
    status = get_engine_status()
    if not status["available"]:
        return {
            "ok": False,
            "answer": status["message"],
            "model": None,
        }

    prompt = "\n\n".join(
        [
            build_context(report, system_map, maintenance_report, request_plan),
            "User question:",
            question.strip(),
            "",
            "Answer in a friendly, concise way. Use short paragraphs or flat bullets if needed.",
        ]
    )
    try:
        data = _post_json(
            "/api/generate",
            {
                "model": status["selected_model"],
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.3},
            },
        )
    except urllib.error.URLError as exc:
        return {"ok": False, "answer": f"Could not reach Ollama while generating: {exc.reason}", "model": None}

    return {
        "ok": True,
        "answer": data.get("response", "").strip() or "The local model returned an empty answer.",
        "model": status["selected_model"],
    }
