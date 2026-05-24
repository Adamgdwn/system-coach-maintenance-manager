"""Local-model Pop!_OS/COSMIC analysis and action ranking."""

from __future__ import annotations

import json
import urllib.error
from typing import Any

from .ai_engine import _extract_json_object, _post_json, choose_request_brain_models, get_engine_status


ACTION_KEYS = {
    "deep-scan-standard",
    "collect-cosmic-user-logs",
    "collect-display-state",
    "collect-update-state",
    "collect-firmware-visibility",
    "collect-package-state",
    "open-cosmic-settings",
    "open-cosmic-store",
    "apply-cosmic-display-layout",
    "apt-repair-step",
    "firmware-review",
    "manual",
}


def _scan_summary(scan: dict) -> dict:
    profile = scan.get("profile", {})
    return {
        "scope": scan.get("scope"),
        "applicable": scan.get("applicable"),
        "profile": {
            "pretty_name": profile.get("pretty_name"),
            "pop_version": profile.get("pop_version"),
            "is_pop_os": profile.get("is_pop_os"),
            "has_cosmic_signal": profile.get("has_cosmic_signal"),
            "session": profile.get("session", {}),
            "cosmic_present": profile.get("cosmic", {}).get("present", []),
        },
        "findings": scan.get("findings", [])[:12],
        "update_state": scan.get("groups", {}).get("updates", {}),
        "user_services": scan.get("groups", {}).get("user_services", {}),
    }


def _fallback_analysis(symptom: str, scan: dict, research: list[dict], lessons: list[dict]) -> dict:
    lowered = symptom.lower()
    actions = [
        {
            "action_key": "deep-scan-standard",
            "title": "Run or refresh Pop!_OS/COSMIC deep scan",
            "why": "Fresh local evidence is the safest first step before changing the desktop session.",
            "risk": "read_only",
            "requires_privilege": False,
            "expected_effect": "Collect current evidence without changing the machine.",
            "side_effects": [],
            "rollback": ["No machine change is made."],
            "verification": ["Review generated scan findings."],
        }
    ]
    likely_surface = "unknown"
    if any(term in lowered for term in ("display", "monitor", "dock", "cursor", "pointer")):
        likely_surface = "display"
        actions.insert(
            0,
            {
                "action_key": "collect-display-state",
                "title": "Collect COSMIC display and input state",
                "why": "The symptom mentions display, dock, cursor, or monitor behavior.",
                "risk": "read_only",
                "requires_privilege": False,
                "expected_effect": "Capture display topology and UI log evidence.",
                "side_effects": [],
                "rollback": ["No machine change is made."],
                "verification": ["Compare display evidence to the reported symptom."],
            },
        )
    elif any(term in lowered for term in ("update", "store", "package", "apt")):
        likely_surface = "package"
        actions.insert(
            0,
            {
                "action_key": "collect-update-state",
                "title": "Collect Pop/COSMIC update state",
                "why": "The symptom mentions updates, COSMIC Store, or packages.",
                "risk": "read_only",
                "requires_privilege": False,
                "expected_effect": "Capture package health and visible update state without installing anything.",
                "side_effects": [],
                "rollback": ["No package change is made."],
                "verification": ["Review apt health and update-list findings."],
            },
        )
    elif any(term in lowered for term in ("settings", "accessibility", "appearance")):
        likely_surface = "session"
        actions.insert(
            0,
            {
                "action_key": "open-cosmic-settings",
                "title": "Open COSMIC Settings",
                "why": "The symptom may be a user-level COSMIC setting.",
                "risk": "low",
                "requires_privilege": False,
                "expected_effect": "Open settings so the user can inspect the target page.",
                "side_effects": ["A settings window opens."],
                "rollback": ["Close COSMIC Settings without saving changes."],
                "verification": ["User confirms whether the setting exists or changed behavior."],
            },
        )
    return {
        "ok": True,
        "source": "deterministic-fallback",
        "model": None,
        "working_problem": symptom or "Pop!_OS/COSMIC health review",
        "likely_surface": likely_surface,
        "hypotheses": [
            {
                "id": "H1",
                "summary": "Local evidence should be refreshed before selecting a fix.",
                "supporting_evidence": [finding.get("summary", "") for finding in scan.get("findings", [])[:4]],
                "contradicting_evidence": [],
                "confidence": 0.35,
                "next_evidence_needed": ["Run the recommended read-only collection action."],
            }
        ],
        "ranked_actions": actions,
        "questions": [],
        "sources_used": [record.get("source_id") for record in research[:4]],
        "lessons_used": [lesson.get("timestamp") for lesson in lessons[:4]],
        "confidence": 0.35,
    }


def _clean_analysis(parsed: dict, symptom: str, scan: dict, research: list[dict], lessons: list[dict], model: str) -> dict:
    actions = parsed.get("ranked_actions", [])
    if not isinstance(actions, list):
        actions = []
    clean_actions = []
    for item in actions[:8]:
        if not isinstance(item, dict):
            continue
        action_key = str(item.get("action_key", "manual")).strip()
        if action_key not in ACTION_KEYS:
            action_key = "manual"
        clean_actions.append(
            {
                "action_key": action_key,
                "title": str(item.get("title", action_key)).strip() or action_key,
                "why": str(item.get("why", "")).strip(),
                "risk": str(item.get("risk", "blocked")).strip(),
                "requires_privilege": bool(item.get("requires_privilege")),
                "expected_effect": str(item.get("expected_effect", "")).strip(),
                "side_effects": [str(value).strip() for value in item.get("side_effects", []) if str(value).strip()]
                if isinstance(item.get("side_effects", []), list)
                else [],
                "rollback": [str(value).strip() for value in item.get("rollback", []) if str(value).strip()]
                if isinstance(item.get("rollback", []), list)
                else [],
                "verification": [str(value).strip() for value in item.get("verification", []) if str(value).strip()]
                if isinstance(item.get("verification", []), list)
                else [],
            }
        )
    if not clean_actions:
        return _fallback_analysis(symptom, scan, research, lessons)
    hypotheses = parsed.get("hypotheses", [])
    if not isinstance(hypotheses, list):
        hypotheses = []
    return {
        "ok": True,
        "source": "local-model",
        "model": model,
        "working_problem": str(parsed.get("working_problem", symptom)).strip(),
        "likely_surface": str(parsed.get("likely_surface", "unknown")).strip(),
        "hypotheses": hypotheses[:6],
        "ranked_actions": clean_actions,
        "questions": [str(value).strip() for value in parsed.get("questions", []) if str(value).strip()]
        if isinstance(parsed.get("questions", []), list)
        else [],
        "sources_used": [str(value).strip() for value in parsed.get("sources_used", []) if str(value).strip()]
        if isinstance(parsed.get("sources_used", []), list)
        else [],
        "lessons_used": [lesson.get("timestamp") for lesson in lessons[:4]],
        "confidence": parsed.get("confidence"),
    }


def build_pop_cosmic_prompt(symptom: str, scan: dict, research: list[dict], lessons: list[dict]) -> str:
    return "\n".join(
        [
            "You are the local Pop!_OS + COSMIC maintenance reasoning brain.",
            "Diagnose deeply by default. Research when permitted. Recommend whitelisted action_key values only.",
            "Do not write raw shell commands. Deterministic code maps action_key values to exact approved actions.",
            "Local evidence beats web research when they conflict.",
            "Return only JSON with keys: working_problem, likely_surface, hypotheses, ranked_actions, questions, sources_used, confidence.",
            "Allowed action_key values: " + ", ".join(sorted(ACTION_KEYS)),
            "",
            "Risk rules:",
            "- read_only for evidence collection",
            "- low for opening user apps/settings",
            "- medium/high only for actions that need stronger approval",
            "- blocked/manual for release upgrade, OS refresh, firmware schedule/install, package purge, broad config deletion, or guessed service restarts",
            "",
            f"User symptom: {symptom or 'No symptom supplied; general Pop/COSMIC review.'}",
            f"Scan summary JSON: {json.dumps(_scan_summary(scan), ensure_ascii=True)[:12000]}",
            f"Research JSON: {json.dumps(research[:8], ensure_ascii=True)[:8000]}",
            f"Local lessons JSON: {json.dumps(lessons[:8], ensure_ascii=True)[:6000]}",
        ]
    )


def analyze_pop_cosmic_issue(symptom: str, scan: dict, research: list[dict] | None = None, lessons: list[dict] | None = None) -> dict:
    research = research or []
    lessons = lessons or []
    status = get_engine_status()
    models = choose_request_brain_models(status.get("models", [])) if status.get("available") else []
    if not models:
        return _fallback_analysis(symptom, scan, research, lessons)
    prompt = build_pop_cosmic_prompt(symptom, scan, research, lessons)
    last_error: Exception | None = None
    for model in models:
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
                timeout=45,
            )
            parsed = _extract_json_object(data.get("response", ""))
            return _clean_analysis(parsed, symptom, scan, research, lessons, model)
        except (urllib.error.URLError, json.JSONDecodeError, ValueError) as exc:
            last_error = exc
    fallback = _fallback_analysis(symptom, scan, research, lessons)
    fallback["model_error"] = str(last_error)
    return fallback


def analyze_pop_cosmic_action_result(plan: dict, result: dict, post_scan: dict) -> dict:
    status = result.get("status", "unknown")
    return {
        "status": status,
        "summary": "Action completed and post-scan evidence was collected." if status == "completed" else "Action did not complete.",
        "verification": post_scan.get("findings", []),
        "lesson_result": "improved" if status == "completed" else "unknown",
    }
