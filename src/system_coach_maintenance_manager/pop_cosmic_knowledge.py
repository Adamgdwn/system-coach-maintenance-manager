"""Local Pop!_OS/COSMIC research and lesson cache."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any

from .maintenance_history import history_dir


RESEARCH_FILE_NAME = "pop-cosmic-research-cache.jsonl"
LESSONS_FILE_NAME = "pop-cosmic-lessons.jsonl"
ACTIONS_FILE_NAME = "pop-cosmic-actions.jsonl"


def _now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def _path(name: str, base_dir: Path | None = None) -> Path:
    return (base_dir or history_dir()) / name


def _append_jsonl(path: Path, payload: dict) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    record = dict(payload)
    record.setdefault("timestamp", _now())
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    return record


def _read_jsonl(path: Path) -> list[dict]:
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
                continue
    return records


def profile_hash(profile: dict) -> str:
    material = json.dumps(
        {
            "pop_version": profile.get("pop_version"),
            "pretty_name": profile.get("pretty_name"),
            "session": profile.get("session", {}),
            "cosmic": profile.get("cosmic", {}).get("present", []),
        },
        sort_keys=True,
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]


def save_research_records(records: list[dict], base_dir: Path | None = None) -> list[dict]:
    path = _path(RESEARCH_FILE_NAME, base_dir)
    return [_append_jsonl(path, record) for record in records]


def load_relevant_research(symptom: str, profile: dict, base_dir: Path | None = None) -> list[dict]:
    terms = {term for term in symptom.lower().split() if len(term) > 3}
    pop_version = str(profile.get("pop_version", ""))
    records = list(reversed(_read_jsonl(_path(RESEARCH_FILE_NAME, base_dir))))
    relevant = []
    for record in records:
        haystack = " ".join(
            str(record.get(key, "")) for key in ("title", "summary", "url", "trust_level", "provider")
        ).lower()
        applies = record.get("applies_to", {})
        score = sum(1 for term in terms if term in haystack)
        if pop_version and pop_version in str(applies):
            score += 2
        if score:
            relevant.append({**record, "relevance_score": score})
        if len(relevant) >= 8:
            break
    return relevant


def save_lesson(lesson: dict, base_dir: Path | None = None) -> dict:
    return _append_jsonl(_path(LESSONS_FILE_NAME, base_dir), lesson)


def load_relevant_lessons(symptom: str, profile: dict, base_dir: Path | None = None) -> list[dict]:
    terms = {term for term in symptom.lower().split() if len(term) > 3}
    current_hash = profile_hash(profile)
    lessons = list(reversed(_read_jsonl(_path(LESSONS_FILE_NAME, base_dir))))
    relevant = []
    for lesson in lessons:
        haystack = " ".join(str(lesson.get(key, "")) for key in ("symptom", "evidence_summary", "action_taken", "verification")).lower()
        score = sum(1 for term in terms if term in haystack)
        if lesson.get("profile_hash") == current_hash:
            score += 2
        if score:
            relevant.append({**lesson, "relevance_score": score})
        if len(relevant) >= 8:
            break
    return relevant


def save_action_record(action: dict, base_dir: Path | None = None) -> dict:
    return _append_jsonl(_path(ACTIONS_FILE_NAME, base_dir), action)


def clear_pop_cosmic_memory(base_dir: Path | None = None) -> None:
    for name in (RESEARCH_FILE_NAME, LESSONS_FILE_NAME, ACTIONS_FILE_NAME):
        path = _path(name, base_dir)
        if path.exists():
            path.unlink()


def make_lesson(
    *,
    symptom: str,
    profile: dict,
    evidence_summary: str,
    action_taken: str,
    result: str,
    verification: str,
    rollback_used: bool = False,
    user_note: str = "",
) -> dict[str, Any]:
    return {
        "timestamp": _now(),
        "symptom": symptom,
        "profile_hash": profile_hash(profile),
        "pop_version": profile.get("pop_version", "unknown"),
        "cosmic_session": profile.get("session", {}).get("current_desktop", "unknown"),
        "evidence_summary": evidence_summary,
        "action_taken": action_taken,
        "result": result,
        "rollback_used": rollback_used,
        "verification": verification,
        "user_note": user_note,
    }
