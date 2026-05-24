"""Local AI coaching engine backed by Ollama."""

from __future__ import annotations

import json
import re
from typing import Any
import urllib.error
import urllib.request

from .troubleshooting_model import troubleshooting_prompt_block


OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_TIMEOUT = 45
PREFERRED_MODELS = ["gemma4:latest", "gemma4", "gemma4:e4b", "qwen3:8b", "qwen3", "llama3.1:8b", "mistral"]
REQUEST_BRAIN_MODELS = ["gemma4:latest", "gemma4", "gemma4:e4b"]
GEMMA4_MODEL_PREFIX = "gemma4"
REQUEST_FAMILIES = {
    "unknown",
    "cursor-size",
    "display",
    "display-dock",
    "display-layout-fix",
    "audio-routing",
    "network-dns",
    "package-updates",
    "docker-cleanup",
    "startup-apps",
    "slow-computer",
}


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
        if _is_gemma4_model(preferred) and preferred in models:
            return preferred
    gemma4_model = _first_available_gemma4_model(models)
    if gemma4_model:
        return gemma4_model
    for preferred in PREFERRED_MODELS:
        if preferred in models:
            return preferred
    return models[0]


def choose_request_brain_model(models: list[str]) -> str | None:
    if not models:
        return None
    for preferred in REQUEST_BRAIN_MODELS:
        if preferred in models:
            return preferred
    return _first_available_gemma4_model(models)


def _first_available_gemma4_model(models: list[str]) -> str | None:
    for model in models:
        if _is_gemma4_model(model):
            return model
    return None


def _is_gemma4_model(model: str) -> bool:
    normalized = model.strip().lower()
    return normalized == GEMMA4_MODEL_PREFIX or normalized.startswith(f"{GEMMA4_MODEL_PREFIX}:")


def _extract_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?", "", stripped, flags=re.IGNORECASE).strip()
        stripped = re.sub(r"```$", "", stripped).strip()
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
        if not match:
            raise
        parsed = json.loads(match.group(0))
    if not isinstance(parsed, dict):
        raise ValueError("model response was not a JSON object")
    return parsed


def _strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", text)


def _compact_request_evidence(evidence: dict | None) -> dict:
    if not evidence:
        return {}
    compact = {
        "generated_at": evidence.get("generated_at"),
        "os": evidence.get("os"),
        "desktop_hint": evidence.get("desktop_hint"),
        "scopes": evidence.get("scopes", []),
        "facts": evidence.get("facts", {}),
        "commands": [],
    }
    for command in evidence.get("commands", [])[:12]:
        compact["commands"].append(
            {
                "command": command.get("command"),
                "exit_code": command.get("exit_code"),
                "output_excerpt": _strip_ansi(str(command.get("output", "")))[:1200],
            }
        )
    return compact


def _family_from_evidence(evidence: dict | None) -> str | None:
    if not evidence:
        return None
    for scope in evidence.get("scopes", []):
        if scope in REQUEST_FAMILIES and scope != "unknown":
            return scope
    return None


def build_request_reasoning_prompt(
    request_text: str,
    *,
    os_name: str | None = None,
    desktop_hint: str | None = None,
    maintenance_report: dict | None = None,
    request_evidence: dict | None = None,
    learning_context: list[str] | None = None,
) -> str:
    findings = []
    if maintenance_report:
        for finding in maintenance_report.get("findings", [])[:8]:
            findings.append(
                {
                    "title": finding.get("title"),
                    "severity": finding.get("severity"),
                    "summary": finding.get("summary"),
                    "evidence": finding.get("evidence"),
                }
            )

    compact_evidence = _compact_request_evidence(request_evidence)
    return "\n".join(
        [
            "You are Gemma acting as the thinking brain for System Coach and Maintenance Manager.",
            troubleshooting_prompt_block(),
            "",
            "Build an evidence-based troubleshooting hypothesis for the user's maintenance request.",
            "The family is the current investigation lane, not a final diagnosis. Evidence may overturn it later.",
            "Do not invent shell commands. Do not approve execution. The deterministic planner will choose commands later.",
            "Return only a JSON object with these keys:",
            (
                "family, alternate_families, ready, acknowledgement, questions, evidence_assessment, "
                "investigation_steps, permission_plan, reasoning_summary, confidence"
            ),
            "Allowed family values:",
            ", ".join(sorted(REQUEST_FAMILIES)),
            "",
            "Reasoning rules:",
            "- Choose the lane that gathers the most useful first evidence; do not treat the lane as the answer.",
            "- Use display-dock as an investigation lane for external monitor, dock, rotation, hidden screen area, DisplayLink, jittery pointer tied to a display, or compositor/display symptoms.",
            "- Use cursor-size only when the request is specifically about pointer size or visibility without display/dock symptoms.",
            "- List plausible alternate_families when the evidence could point somewhere else.",
            "- In evidence_assessment, say what evidence supports the current lane and what could disprove it.",
            "- In investigation_steps, list the next 2-5 evidence or fix steps in order.",
            "- In permission_plan, state what can run as the current user and what would need admin/manual approval.",
            "- Use unknown with questions when the target is too vague.",
            "- Do not ask the user for facts already visible in the read-only request evidence.",
            "- If evidence includes device names, monitor names, routes, services, logs, or package output, use those facts directly.",
            "- If read-only request evidence has a relevant scope, treat that as a strong hint for the first investigation lane.",
            "- Keep acknowledgement plain and specific.",
            "- Set ready=true when evidence is good enough to start a guarded investigation or fix plan.",
            "- Ask questions only when the missing answer would change the plan family or safety decision.",
            "- Ask at most two questions.",
            "",
            f"Operating system: {os_name or 'unknown'}",
            f"Desktop/session hint: {desktop_hint or 'unknown'}",
            f"Recent maintenance findings JSON: {json.dumps(findings, ensure_ascii=True)[:6000]}",
            f"Read-only request evidence JSON: {json.dumps(compact_evidence, ensure_ascii=True)[:10000]}",
            f"Local learning notes JSON: {json.dumps((learning_context or [])[:8], ensure_ascii=True)[:4000]}",
            "",
            "User request:",
            request_text.strip(),
        ]
    )


def reason_about_request(
    request_text: str,
    *,
    os_name: str | None = None,
    desktop_hint: str | None = None,
    maintenance_report: dict | None = None,
    request_evidence: dict | None = None,
    learning_context: list[str] | None = None,
) -> dict[str, Any]:
    """Use the local model as the Request Desk reasoning layer.

    The model may classify and explain a request, but it cannot supply executable
    commands. Command selection stays inside the guarded planner.
    """

    status = get_engine_status()
    if not status["available"]:
        return {
            "ok": False,
            "source": "unavailable",
            "model": None,
            "family": "unknown",
            "ready": False,
            "acknowledgement": status["message"],
            "questions": ["Start Ollama with the configured Gemma model, or prepare a plan from deterministic rules."],
            "reasoning_summary": "Local model was not available.",
        }
    request_model = choose_request_brain_model(status.get("models", []))
    if not request_model:
        return {
            "ok": False,
            "source": "unavailable",
            "model": None,
            "family": "unknown",
            "ready": False,
            "acknowledgement": "Gemma 4 is not available in Ollama, so the Request Desk reasoning brain is offline.",
            "questions": ["Install or start the configured gemma4:latest model, then try the Request Desk again."],
            "reasoning_summary": "Configured Gemma 4 request brain was not available.",
        }

    prompt = build_request_reasoning_prompt(
        request_text,
        os_name=os_name,
        desktop_hint=desktop_hint,
        maintenance_report=maintenance_report,
        request_evidence=request_evidence,
        learning_context=learning_context,
    )

    try:
        data = _post_json(
            "/api/generate",
            {
                "model": request_model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.1},
            },
            timeout=30,
        )
        parsed = _extract_json_object(data.get("response", ""))
    except (urllib.error.URLError, json.JSONDecodeError, ValueError) as exc:
        return {
            "ok": False,
            "source": "model-error",
            "model": request_model,
            "family": "unknown",
            "ready": False,
            "acknowledgement": f"Gemma could not return a usable request analysis: {exc}",
            "questions": ["Try again, or prepare a plan from deterministic rules."],
            "reasoning_summary": "Local model request analysis failed.",
        }

    family = str(parsed.get("family", "unknown")).strip()
    if family not in REQUEST_FAMILIES:
        family = "unknown"
    evidence_family = _family_from_evidence(request_evidence)
    if evidence_family == "display-dock" and family in {"unknown", "display", "cursor-size"}:
        family = evidence_family
    elif family == "unknown" and evidence_family:
        family = evidence_family
    questions = parsed.get("questions", [])
    if not isinstance(questions, list):
        questions = []
    clean_questions = [str(item).strip() for item in questions if str(item).strip()][:3]
    alternates = parsed.get("alternate_families", [])
    if not isinstance(alternates, list):
        alternates = []
    clean_alternates = [str(item).strip() for item in alternates if str(item).strip() in REQUEST_FAMILIES and str(item).strip() != family][:4]
    investigation_steps = parsed.get("investigation_steps", [])
    if not isinstance(investigation_steps, list):
        investigation_steps = []
    clean_investigation_steps = [str(item).strip() for item in investigation_steps if str(item).strip()][:5]
    acknowledgement = str(parsed.get("acknowledgement", "")).strip()
    if not acknowledgement:
        if evidence_family:
            acknowledgement = f"I collected local evidence and matched this to the {evidence_family} troubleshooting path."
        else:
            acknowledgement = "I reviewed the request with the local model."

    return {
        "ok": True,
        "source": "gemma",
        "model": request_model,
        "family": family,
        "ready": bool(parsed.get("ready") or (family != "unknown" and evidence_family)),
        "acknowledgement": acknowledgement,
        "questions": clean_questions,
        "alternate_families": clean_alternates,
        "evidence_assessment": str(parsed.get("evidence_assessment", "")).strip(),
        "investigation_steps": clean_investigation_steps,
        "permission_plan": str(parsed.get("permission_plan", "")).strip(),
        "reasoning_summary": str(parsed.get("reasoning_summary", "")).strip(),
        "confidence": parsed.get("confidence"),
    }


def analyze_action_result(plan: dict, result: dict) -> dict[str, Any]:
    """Ask Gemma to turn executed command output into a useful next-step summary."""

    status = get_engine_status()
    request_model = choose_request_brain_model(status.get("models", [])) if status.get("available") else None
    if not request_model:
        return {
            "ok": False,
            "model": None,
            "analysis": "Gemma analysis is unavailable. Review the command output directly.",
        }

    output = _strip_ansi(str(result.get("output", "")))[:12000]
    prompt = "\n".join(
        [
            "You are Gemma acting as the maintenance reasoning brain after an approved Execute action.",
            troubleshooting_prompt_block(),
            "",
            "The user wants concise, useful troubleshooting, not generic caveats.",
            "Use the command output to explain what was found and the best next fix direction.",
            "Do not invent commands. Do not claim a fix was applied unless the result shows it.",
            "If the action only collected evidence, reassess the original hypothesis. Say what supports it, what contradicts it, and what the next guarded fix or investigation lane should be.",
            "Write plain text with these short sections:",
            "What I found",
            "Hypothesis check",
            "Most likely cause",
            "Best next fix",
            "Can execute now",
            "",
            f"Plan JSON: {json.dumps(plan, ensure_ascii=True)[:6000]}",
            f"Action result JSON: {json.dumps({k: v for k, v in result.items() if k != 'output'}, ensure_ascii=True)[:4000]}",
            "Command output:",
            output or "No command output was returned.",
        ]
    )
    try:
        data = _post_json(
            "/api/generate",
            {
                "model": request_model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.15},
            },
            timeout=30,
        )
    except urllib.error.URLError as exc:
        return {"ok": False, "model": request_model, "analysis": f"Could not reach Gemma for result analysis: {exc.reason}"}

    return {
        "ok": True,
        "model": request_model,
        "analysis": data.get("response", "").strip() or "Gemma returned an empty result analysis.",
    }


def build_context(
    report: dict | None,
    system_map: dict | None = None,
    maintenance_report: dict | None = None,
    request_plan: dict | None = None,
) -> str:
    if not report:
        return "No system report is available yet. Ask the user to run a local review first."

    lines = [
        "You are a local desktop coaching assistant for System Coach and Maintenance Manager.",
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
