"""Local history archive for maintenance diagnostics and request plans."""

from __future__ import annotations

from collections import Counter
import copy
import datetime as dt
import json
import os
from pathlib import Path
import uuid


HISTORY_FILE_NAME = "maintenance-history.jsonl"
RECENT_FIX_WINDOW_HOURS = 24


def _now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def history_dir() -> Path:
    configured = os.environ.get("SYSTEM_COACH_HISTORY_DIR")
    if configured:
        return Path(configured).expanduser()
    return Path.cwd() / "history"


def history_path(base_dir: Path | None = None) -> Path:
    return (base_dir or history_dir()) / HISTORY_FILE_NAME


def _new_record_id(recorded_at: str) -> str:
    safe_timestamp = recorded_at.replace(":", "").replace("-", "").replace("T", "-")
    return f"{safe_timestamp}-{uuid.uuid4().hex[:8]}"


def _maintenance_summary(report: dict) -> dict:
    summary = report.get("summary", {})
    return {
        "finding_count": summary.get("finding_count", 0),
        "severity_counts": summary.get("severity_counts", {}),
        "approval_required_count": summary.get("approval_required_count", 0),
        "execution_enabled": summary.get("execution_enabled", False),
    }


def _request_plan_summary(plan: dict) -> dict:
    return {
        "title": plan.get("title", "Request plan"),
        "family": plan.get("family", "unknown"),
        "platform": plan.get("platform", "Unknown"),
        "risk": plan.get("risk", "unknown"),
        "approval_required": plan.get("approval_required", True),
        "execution_enabled": plan.get("execution_enabled", False),
        "requires_privilege": plan.get("requires_privilege", False),
    }


def _approval_decision_summary(decision: dict) -> dict:
    return {
        "decision": decision.get("decision", "unknown"),
        "plan_id": decision.get("plan_id"),
        "plan_title": decision.get("plan_title"),
        "reason": decision.get("reason", ""),
    }


def _action_result_summary(result: dict) -> dict:
    return {
        "action_id": result.get("action_id"),
        "plan_id": result.get("plan_id"),
        "status": result.get("status", "unknown"),
        "exit_code": result.get("exit_code"),
        "execution_enabled": result.get("execution_enabled", False),
    }


def _learning_note_summary(note: dict) -> dict:
    return {
        "family": note.get("family", "unknown"),
        "status": note.get("status", "unknown"),
        "lesson": str(note.get("lesson", ""))[:180],
        "followup_family": note.get("followup_family"),
    }


def _summary_for(kind: str, payload: dict) -> dict:
    if kind == "maintenance_report":
        return _maintenance_summary(payload)
    if kind == "request_plan":
        return _request_plan_summary(payload)
    if kind == "approval_decision":
        return _approval_decision_summary(payload)
    if kind == "action_result":
        return _action_result_summary(payload)
    if kind == "learning_note":
        return _learning_note_summary(payload)
    return {"kind": kind}


def append_history_record(kind: str, payload: dict, base_dir: Path | None = None) -> dict:
    """Append a local-only history record and return the stored record."""

    recorded_at = _now()
    record = {
        "id": _new_record_id(recorded_at),
        "recorded_at": recorded_at,
        "kind": kind,
        "summary": _summary_for(kind, payload),
        "payload": payload,
    }
    path = history_path(base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    return record


def record_maintenance_report(report: dict, base_dir: Path | None = None) -> dict:
    return append_history_record("maintenance_report", report, base_dir=base_dir)


def record_request_plan(plan: dict, base_dir: Path | None = None) -> dict:
    return append_history_record("request_plan", plan, base_dir=base_dir)


def record_approval_decision(decision: dict, base_dir: Path | None = None) -> dict:
    return append_history_record("approval_decision", decision, base_dir=base_dir)


def record_action_result(result: dict, base_dir: Path | None = None) -> dict:
    return append_history_record("action_result", result, base_dir=base_dir)


def record_learning_note(note: dict, base_dir: Path | None = None) -> dict:
    return append_history_record("learning_note", note, base_dir=base_dir)


def _read_records(base_dir: Path | None = None) -> list[dict]:
    path = history_path(base_dir)
    if not path.exists():
        return []

    records = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                records.append(
                    {
                        "id": "corrupt-history-line",
                        "recorded_at": None,
                        "kind": "history_error",
                        "summary": {"error": "A history record could not be parsed."},
                        "payload": {"raw": line[:500]},
                    }
                )
    return records


def _parse_recorded_at(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    try:
        return dt.datetime.fromisoformat(value)
    except ValueError:
        return None


def _record_is_recent(record: dict, *, now: dt.datetime, max_age_hours: int) -> bool:
    recorded_at = _parse_recorded_at(record.get("recorded_at"))
    if not recorded_at:
        return False
    return (now - recorded_at) <= dt.timedelta(hours=max_age_hours)


def _action_result_family(result: dict) -> str | None:
    plan_id = str(result.get("plan_id") or "")
    action_id = str(result.get("action_id") or "")
    commands = " ".join(str(command) for command in result.get("commands", []))
    haystack = f"{plan_id} {action_id} {commands}".lower()
    if "pop-cosmic-panel-restart" in haystack or "pkill -term -x cosmic-panel" in haystack:
        return "pop-cosmic-panel-restart"
    if "display-layout-fix" in haystack or "cosmic-randr mode" in haystack:
        return "display-layout-fix"
    return None


def _recent_completed_fix_families(records: list[dict], *, max_age_hours: int) -> dict[str, dict]:
    now = dt.datetime.now()
    fixed: dict[str, dict] = {}
    for record in reversed(records):
        if not _record_is_recent(record, now=now, max_age_hours=max_age_hours):
            continue
        if record.get("kind") != "action_result":
            continue
        result = record.get("payload", {})
        if result.get("status") != "completed":
            continue
        family = _action_result_family(result)
        if family and family not in fixed:
            fixed[family] = {
                "family": family,
                "recorded_at": record.get("recorded_at"),
                "action_id": result.get("action_id"),
                "plan_id": result.get("plan_id"),
                "commands": result.get("commands", []),
            }
    return fixed


def _resolution_for_finding(finding: dict, recent_fixes: dict[str, dict]) -> dict | None:
    if finding.get("id") == "journal-errors" and "pop-cosmic-panel-restart" in recent_fixes:
        evidence = finding.get("evidence", {})
        sample = " ".join(str(item) for item in evidence.get("sample", []))
        journal_text = f"{finding.get('summary', '')} {sample}".lower()
        if not any(term in journal_text for term in ("cosmic-panel", "cosmicapplet", "cosmic applet", "broken pipe")):
            return None
        fix = recent_fixes["pop-cosmic-panel-restart"]
        return {
            "source": "recent-action-history",
            "fix_family": fix["family"],
            "action_id": fix.get("action_id"),
            "plan_id": fix.get("plan_id"),
            "recorded_at": fix.get("recorded_at"),
            "reason": (
                "A recent approved current-user COSMIC panel restart completed. "
                "The bounded journal query can still contain historical pre-fix panel errors, so this finding is in monitor mode."
            ),
            "verify": "Retest the user-visible COSMIC panel symptom before preparing another log-inspection plan.",
        }
    return None


def _refresh_report_summary(report: dict) -> None:
    findings = report.get("findings", [])
    action_plans = report.get("action_plans", [])
    summary = dict(report.get("summary", {}))
    summary.update(
        {
            "finding_count": len(findings),
            "status_counts": dict(Counter(finding.get("status", "unknown") for finding in findings)),
            "severity_counts": dict(Counter(finding.get("severity", "unknown") for finding in findings)),
            "approval_required_count": len(action_plans),
            "execution_enabled": any(plan.get("execution_enabled") for plan in action_plans),
        }
    )
    report["summary"] = summary


def apply_recent_fix_overrides(
    report: dict,
    *,
    base_dir: Path | None = None,
    max_age_hours: int = RECENT_FIX_WINDOW_HOURS,
) -> dict:
    """Mark findings as recently addressed when local action history supports it.

    This does not delete evidence. It prevents historical diagnostics, especially bounded log
    samples, from repeatedly becoming the same approval backlog immediately after a targeted
    approved fix completed.
    """

    records = _read_records(base_dir)
    recent_fixes = _recent_completed_fix_families(records, max_age_hours=max_age_hours)
    if not recent_fixes:
        return report

    updated = copy.deepcopy(report)
    addressed_finding_ids: set[str] = set()
    for finding in updated.get("findings", []):
        resolution = _resolution_for_finding(finding, recent_fixes)
        if not resolution:
            continue
        addressed_finding_ids.add(str(finding.get("id")))
        original = {
            "status": finding.get("status"),
            "severity": finding.get("severity"),
            "summary": finding.get("summary"),
        }
        finding["status"] = "monitor"
        finding["severity"] = "info"
        finding["can_prepare_action"] = False
        finding["summary"] = f"Recently addressed by {resolution['fix_family']}; monitoring for fresh evidence."
        finding.setdefault("evidence", {})["history_resolution"] = resolution
        finding["evidence"]["history_resolution"]["original_finding"] = original
        finding["recommended_next_steps"] = [
            resolution["verify"],
            "Run a fresh targeted check only if the user-visible symptom returns or new post-fix log lines appear.",
        ]

    if addressed_finding_ids:
        updated["action_plans"] = [
            plan for plan in updated.get("action_plans", []) if str(plan.get("finding_id")) not in addressed_finding_ids
        ]
        updated.setdefault("recommendations", [])
        updated["recommendations"] = [
            "Recent successful fixes moved matching historical findings into monitor mode; verify the symptom before reopening them.",
            *updated["recommendations"],
        ]
        _refresh_report_summary(updated)
    return updated


def _known_good_lessons(records: list[dict]) -> list[str]:
    lessons = []
    for record in reversed(records):
        if record.get("kind") != "maintenance_report":
            continue
        payload = record.get("payload", {})
        severity_counts = payload.get("summary", {}).get("severity_counts", {})
        if not severity_counts.get("critical") and not severity_counts.get("warning"):
            lessons.append(
                f"{record.get('recorded_at')}: maintenance diagnostics had no critical or warning findings."
            )
            break
    return lessons


def _learning_notes(records: list[dict], limit: int = 8) -> list[str]:
    notes = []
    for record in reversed(records):
        if record.get("kind") != "learning_note":
            continue
        payload = record.get("payload", {})
        lesson = str(payload.get("lesson", "")).strip()
        if not lesson:
            continue
        family = payload.get("family", "unknown")
        status = payload.get("status", "unknown")
        followup = payload.get("followup_family")
        suffix = f"; next lane: {followup}" if followup else ""
        notes.append(f"{record.get('recorded_at')}: {family} ended {status}: {lesson}{suffix}.")
        if len(notes) >= limit:
            break
    return notes


def _latest_maintenance_reports(records: list[dict], limit: int = 2) -> list[dict]:
    reports = [record for record in records if record.get("kind") == "maintenance_report"]
    return reports[-limit:]


def _finding_signature(finding: dict) -> str:
    return "|".join(
        [
            str(finding.get("id", "unknown")),
            str(finding.get("severity", "unknown")),
            str(finding.get("status", "unknown")),
            str(finding.get("summary", "")),
        ]
    )


def _changed_since_last(records: list[dict]) -> list[str]:
    latest = _latest_maintenance_reports(records)
    if len(latest) < 2:
        return ["Not enough maintenance history yet to compare diagnostic runs."]

    previous, current = latest
    previous_payload = previous.get("payload", {})
    current_payload = current.get("payload", {})
    previous_findings = {_finding_signature(finding): finding for finding in previous_payload.get("findings", [])}
    current_findings = {_finding_signature(finding): finding for finding in current_payload.get("findings", [])}
    previous_keys = set(previous_findings)
    current_keys = set(current_findings)

    new_findings = [current_findings[key]["title"] for key in sorted(current_keys - previous_keys)]
    resolved_findings = [previous_findings[key]["title"] for key in sorted(previous_keys - current_keys)]
    current_summary = current_payload.get("summary", {})
    previous_summary = previous_payload.get("summary", {})

    changes = [
        f"Compared {previous.get('recorded_at')} to {current.get('recorded_at')}.",
        (
            "Warnings/critical counts changed from "
            f"{previous_summary.get('severity_counts', {})} to {current_summary.get('severity_counts', {})}."
        ),
    ]
    if new_findings:
        changes.append(f"New or changed findings: {', '.join(new_findings[:8])}.")
    if resolved_findings:
        changes.append(f"Resolved or changed findings: {', '.join(resolved_findings[:8])}.")
    if not new_findings and not resolved_findings:
        changes.append("No finding-level changes were detected between the two latest diagnostic snapshots.")
    return changes


def load_history(limit: int = 25, base_dir: Path | None = None) -> dict:
    records = _read_records(base_dir)
    recent = list(reversed(records))[:limit]
    counts = Counter(record.get("kind", "unknown") for record in records)
    return {
        "path": str(history_path(base_dir)),
        "summary": {
            "record_count": len(records),
            "kind_counts": dict(counts),
        },
        "known_good_lessons": _known_good_lessons(records),
        "learning_notes": _learning_notes(records),
        "changed_since_last": _changed_since_last(records),
        "records": recent,
    }


def format_history(history: dict) -> str:
    lines = [
        f"History path: {history['path']}",
        f"Records: {history['summary']['record_count']}",
        f"Kind counts: {json.dumps(history['summary']['kind_counts'], indent=2)}",
        "",
        "Known-good lessons:",
    ]
    lessons = history.get("known_good_lessons", [])
    lines.extend(f"- {lesson}" for lesson in lessons)
    if not lessons:
        lines.append("- No evidence-backed known-good lessons yet.")

    lines.extend(["", "Learning notes:"])
    learning_notes = history.get("learning_notes", [])
    lines.extend(f"- {lesson}" for lesson in learning_notes)
    if not learning_notes:
        lines.append("- No action-result learning notes yet.")

    lines.extend(["", "Changed since last diagnostic run:"])
    lines.extend(f"- {change}" for change in history.get("changed_since_last", []))

    lines.extend(["", "Recent records:"])
    for record in history.get("records", []):
        lines.extend(
            [
                f"- {record.get('recorded_at')} | {record.get('kind')} | {record.get('id')}",
                f"  {json.dumps(record.get('summary', {}), sort_keys=True)}",
            ]
        )
    if not history.get("records"):
        lines.append("- No history records yet.")
    return "\n".join(lines)
