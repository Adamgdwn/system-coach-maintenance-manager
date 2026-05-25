"""Local AI coaching engine backed by Ollama."""

from __future__ import annotations

import json
import re
from typing import Any
import urllib.error
import urllib.request

from .model_providers import configured_ollama_url
from .troubleshooting_model import troubleshooting_prompt_block


OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_TIMEOUT = 45
PREFERRED_MODELS = [
    "qwen3:8b",
    "qwen3",
    "gemma4:latest",
    "gemma4",
    "gemma4:e4b",
    "gemma4:26b",
    "gemma4:31b",
    "deepseek-r1:14b",
    "deepseek-r1",
    "gpt-oss:20b",
    "gpt-oss",
    "gptoss",
    "qwen3-vl:8b",
    "llama3.1:8b",
    "mistral",
]
REQUEST_BRAIN_MODELS = ["qwen3:8b", "qwen3", "gemma4:latest", "gemma4", "gemma4:e4b", "deepseek-r1:14b", "gpt-oss:20b"]
REQUEST_FAMILIES = {
    "unknown",
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
}


def _post_json(path: str, payload: dict[str, Any], timeout: int = DEFAULT_TIMEOUT) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{configured_ollama_url()}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def _get_json(path: str, timeout: int = 5) -> dict[str, Any]:
    with urllib.request.urlopen(f"{configured_ollama_url()}{path}", timeout=timeout) as response:
        return json.load(response)


def get_engine_status() -> dict[str, Any]:
    base_url = configured_ollama_url()
    try:
        data = _get_json("/api/tags")
    except urllib.error.URLError as exc:
        return {
            "available": False,
            "provider": "ollama",
            "models": [],
            "selected_model": None,
            "message": f"Ollama is not reachable on {base_url}: {exc.reason}",
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


def choose_request_brain_model(models: list[str]) -> str | None:
    candidates = choose_request_brain_models(models)
    return candidates[0] if candidates else None


def choose_request_brain_models(models: list[str]) -> list[str]:
    if not models:
        return []
    selected: list[str] = []
    for preferred in REQUEST_BRAIN_MODELS:
        if preferred in models:
            selected.append(preferred)
    for model in models:
        if model not in selected:
            selected.append(model)
    return selected


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
            "You are the local thinking brain for System Coach and Maintenance Manager.",
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
            "questions": ["Start Ollama with a supported local model, or prepare a plan from deterministic rules."],
            "reasoning_summary": "Local model was not available.",
        }
    request_models = choose_request_brain_models(status.get("models", []))
    if not request_models:
        return {
            "ok": False,
            "source": "unavailable",
            "model": None,
            "family": "unknown",
            "ready": False,
            "acknowledgement": "No supported local Request Desk reasoning model is available in Ollama.",
            "questions": ["Install or start a supported local model, then try the Request Desk again."],
            "reasoning_summary": "Configured local request brain was not available.",
        }

    prompt = build_request_reasoning_prompt(
        request_text,
        os_name=os_name,
        desktop_hint=desktop_hint,
        maintenance_report=maintenance_report,
        request_evidence=request_evidence,
        learning_context=learning_context,
    )

    request_model = request_models[0]
    parsed: dict[str, Any] | None = None
    last_error: Exception | None = None
    for candidate_model in request_models:
        request_model = candidate_model
        try:
            data = _post_json(
                "/api/generate",
                {
                    "model": candidate_model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0.1},
                },
                timeout=30,
            )
            parsed = _extract_json_object(data.get("response", ""))
            break
        except (urllib.error.URLError, json.JSONDecodeError, ValueError) as exc:
            last_error = exc

    if parsed is None:
        return {
            "ok": False,
            "source": "model-error",
            "model": request_model,
            "family": "unknown",
            "ready": False,
            "acknowledgement": f"No local model returned a usable request analysis: {last_error}",
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
        "source": "local-model",
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


def build_maintenance_reasoning_prompt(
    plan: dict,
    finding: dict,
    *,
    maintenance_report: dict | None = None,
    learning_context: list[str] | None = None,
    changed_since_last: list[str] | None = None,
) -> str:
    """Build the pre-approval maintenance reasoning prompt."""

    peer_findings = []
    if maintenance_report:
        for item in maintenance_report.get("findings", [])[:8]:
            peer_findings.append(
                {
                    "id": item.get("id"),
                    "title": item.get("title"),
                    "severity": item.get("severity"),
                    "summary": item.get("summary"),
                    "evidence": item.get("evidence"),
                }
            )
    plan_contract = plan.get("action_contract", {})
    compact_plan = {
        "id": plan.get("id"),
        "title": plan.get("title"),
        "family": plan.get("family", plan.get("finding_id")),
        "risk": plan.get("risk"),
        "reversible": plan.get("reversible"),
        "requires_privilege": plan.get("requires_privilege"),
        "commands": plan.get("commands", []),
        "expected_effect": plan.get("expected_effect"),
        "manual_steps": plan.get("manual_steps", []),
        "rollback": plan.get("rollback", []),
        "execution_enabled": plan_contract.get("execution_enabled", plan.get("execution_enabled")),
        "execution_mode": plan_contract.get("execution_mode"),
        "gate_reasons": plan_contract.get("execution_gate", {}).get("reasons", []),
    }
    compact_finding = {
        "id": finding.get("id"),
        "title": finding.get("title"),
        "category": finding.get("category"),
        "severity": finding.get("severity"),
        "status": finding.get("status"),
        "summary": finding.get("summary"),
        "evidence": finding.get("evidence"),
        "recommended_next_steps": finding.get("recommended_next_steps", []),
    }
    return "\n".join(
        [
            "You are the local maintenance reasoning brain before an approval dialog.",
            troubleshooting_prompt_block(),
            "",
            "Think like a careful technician. The user needs to know whether the next step is justified before typing APPROVE.",
            "Use the diagnostics, history, and selected plan to reason through the problem.",
            "Do not invent shell commands. The deterministic guarded plan already supplies the only commands that may execute.",
            "Do not claim the command fixes the problem unless it actually changes the system.",
            "Treat evidence-collection commands as investigation steps, not repairs.",
            "Return only JSON with these keys:",
            (
                "working_problem, scenario_review, hypotheses, evidence_assessment, plan_fit, "
                "troubleshooting_path, recommended_next_step, approval_guidance, stop_conditions, confidence"
            ),
            "",
            "Reasoning rules:",
            "- Restate the working problem as a symptom, not a final cause.",
            "- Consider at least two plausible hypotheses when possible.",
            "- Say what current evidence supports and what evidence would disprove the leading hypothesis.",
            "- Explain why this selected plan is or is not the smallest useful next step.",
            "- In troubleshooting_path, list the next 3-6 steps in order, including what to learn after execution.",
            "- In approval_guidance, say exactly what the user is approving and what they are not approving.",
            "- In stop_conditions, name conditions where the user should not approve or should stop after execution.",
            "- Keep the response plain and concrete.",
            "",
            f"Selected finding JSON: {json.dumps(compact_finding, ensure_ascii=True)[:7000]}",
            f"Selected guarded plan JSON: {json.dumps(compact_plan, ensure_ascii=True)[:7000]}",
            f"Peer findings JSON: {json.dumps(peer_findings, ensure_ascii=True)[:8000]}",
            f"Changed since last diagnostics JSON: {json.dumps((changed_since_last or [])[:8], ensure_ascii=True)[:3000]}",
            f"Local learning notes JSON: {json.dumps((learning_context or [])[:8], ensure_ascii=True)[:4000]}",
        ]
    )


def _clean_string_list(value: Any, limit: int = 6) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()][:limit]


def _fallback_maintenance_reasoning(plan: dict, finding: dict, reason: str = "") -> dict[str, Any]:
    finding_id = finding.get("id", "maintenance")
    if finding_id == "journal-errors":
        hypotheses = [
            "A repeated service, device, package, or desktop component is producing critical log messages.",
            "The critical log sample may include stale or secondary errors that need grouping before repair.",
        ]
        recommended = (
            "Run the read-only journal query to collect a wider sample, then group repeated sources before proposing any restart or repair."
        )
        path = [
            "Treat the critical logs as symptoms.",
            "Collect a larger recent error sample.",
            "Group repeated messages by source.",
            "Prepare a separate fix only for the repeated source.",
        ]
    elif finding_id == "package-manager-health":
        hypotheses = [
            "The package database or package-manager source state needs inspection.",
            "A lock, held package, source issue, or interrupted transaction may be the actual cause.",
        ]
        recommended = "Run only the package health check, then prepare a narrower repair if the output identifies one."
        path = [
            "Inspect package health without changing packages.",
            "Identify the exact package-manager failure.",
            "Prepare a named repair plan with rollback.",
        ]
    else:
        hypotheses = [
            "The diagnostic finding may be the direct issue.",
            "The finding may be a secondary symptom caused by another service, device, or configuration problem.",
        ]
        recommended = plan.get("expected_effect", "Run the selected evidence step before proposing a repair.")
        path = list(plan.get("manual_steps", []))[:4] or ["Collect the next narrow evidence step.", "Reassess before changing the machine."]
    return {
        "ok": True,
        "source": "deterministic-maintenance-brief",
        "model": None,
        "working_problem": str(finding.get("summary", plan.get("title", "Maintenance finding"))),
        "scenario_review": "Local model reasoning was unavailable, so the app used its deterministic maintenance troubleshooting rules.",
        "hypotheses": [{"summary": item, "supporting_evidence": [], "contradicting_evidence": []} for item in hypotheses],
        "evidence_assessment": str(finding.get("summary", "")),
        "plan_fit": "This is the smallest currently guarded step for this diagnostics-generated finding.",
        "troubleshooting_path": path,
        "recommended_next_step": recommended,
        "approval_guidance": "Approve only the exact command preview shown in the guarded dialog; this is not blanket approval for repairs.",
        "stop_conditions": [
            "Do not approve if the command preview does not match the issue you want investigated.",
            "Stop after execution if the output points to a different source than expected.",
        ],
        "confidence": None,
        "model_error": reason,
    }


def reason_about_maintenance_plan(
    plan: dict,
    finding: dict,
    *,
    maintenance_report: dict | None = None,
    learning_context: list[str] | None = None,
    changed_since_last: list[str] | None = None,
) -> dict[str, Any]:
    """Use the local model to reason through a diagnostics-generated plan before approval."""

    status = get_engine_status()
    if not status["available"]:
        return _fallback_maintenance_reasoning(plan, finding, status.get("message", "Local model was unavailable."))
    models = choose_request_brain_models(status.get("models", []))
    if not models:
        return _fallback_maintenance_reasoning(plan, finding, "No supported local maintenance reasoning model is available.")

    prompt = build_maintenance_reasoning_prompt(
        plan,
        finding,
        maintenance_report=maintenance_report,
        learning_context=learning_context,
        changed_since_last=changed_since_last,
    )
    last_error: Exception | None = None
    selected_model = models[0]
    for model in models:
        selected_model = model
        try:
            data = _post_json(
                "/api/generate",
                {
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0.1},
                },
                timeout=35,
            )
            parsed = _extract_json_object(data.get("response", ""))
            hypotheses = parsed.get("hypotheses", [])
            clean_hypotheses = []
            if isinstance(hypotheses, list):
                for item in hypotheses[:5]:
                    if isinstance(item, dict):
                        summary = str(item.get("summary", "")).strip()
                        if summary:
                            clean_hypotheses.append(
                                {
                                    "summary": summary,
                                    "supporting_evidence": _clean_string_list(item.get("supporting_evidence", []), 4),
                                    "contradicting_evidence": _clean_string_list(item.get("contradicting_evidence", []), 4),
                                }
                            )
                    else:
                        summary = str(item).strip()
                        if summary:
                            clean_hypotheses.append({"summary": summary, "supporting_evidence": [], "contradicting_evidence": []})
            return {
                "ok": True,
                "source": "local-model",
                "model": selected_model,
                "working_problem": str(parsed.get("working_problem", finding.get("summary", ""))).strip(),
                "scenario_review": str(parsed.get("scenario_review", "")).strip(),
                "hypotheses": clean_hypotheses,
                "evidence_assessment": str(parsed.get("evidence_assessment", "")).strip(),
                "plan_fit": str(parsed.get("plan_fit", "")).strip(),
                "troubleshooting_path": _clean_string_list(parsed.get("troubleshooting_path", []), 6),
                "recommended_next_step": str(parsed.get("recommended_next_step", "")).strip(),
                "approval_guidance": str(parsed.get("approval_guidance", "")).strip(),
                "stop_conditions": _clean_string_list(parsed.get("stop_conditions", []), 6),
                "confidence": parsed.get("confidence"),
            }
        except (urllib.error.URLError, json.JSONDecodeError, ValueError) as exc:
            last_error = exc
    return _fallback_maintenance_reasoning(
        plan,
        finding,
        f"No local model returned a usable maintenance reasoning brief from {selected_model}: {last_error}",
    )


def analyze_action_result(plan: dict, result: dict) -> dict[str, Any]:
    """Ask the local reasoning ladder to turn command output into a useful next-step summary."""

    status = get_engine_status()
    request_model = choose_request_brain_model(status.get("models", [])) if status.get("available") else None
    if not request_model:
        return {
            "ok": False,
            "model": None,
            "analysis": "Local model analysis is unavailable. Review the command output directly.",
        }

    output = _strip_ansi(str(result.get("output", "")))[:12000]
    prompt = "\n".join(
        [
            "You are the local maintenance reasoning brain after an approved Execute action.",
            troubleshooting_prompt_block(),
            "",
            "The user wants concise, useful troubleshooting, not generic caveats.",
            "Use the command output to explain what was found and the best next fix direction.",
            "Do not invent commands. Do not claim a fix was applied unless the result shows it.",
            "If the action only collected evidence, reassess the original hypothesis. Say what supports it, what contradicts it, and what the next guarded fix or investigation lane should be.",
            "For apt/dpkg evidence: if an approved elevated apt-get check completed successfully, treat earlier non-root dpkg lock permission errors as a normal permission boundary, not a stale or corrupted lock.",
            "Never recommend removing /var/lib/dpkg lock files after a successful apt-get check. Only discuss lock removal when command output proves no apt/dpkg process is active and the lock is stale.",
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
        return {"ok": False, "model": request_model, "analysis": f"Could not reach the local model for result analysis: {exc.reason}"}

    return {
        "ok": True,
        "model": request_model,
        "analysis": data.get("response", "").strip() or "The local model returned an empty result analysis.",
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
