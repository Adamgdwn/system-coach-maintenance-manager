"""Conversation engine: session state, history, pending action tracking, and event dispatch."""

from __future__ import annotations

import threading
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from . import autonomy_controls

GREETING_LOADING = "Checking your machine…"
GREETING_HEALTHY = "Everything looks clean — anything on your mind?"
GREETING_PARTIAL_FAILURE = "I couldn't complete all checks — here's what I got."

EVENT_AGENT_TOKEN = "agent_token"
EVENT_ACTION_PROPOSED = "action_proposed"
EVENT_ACTION_RESULT = "action_result"
EVENT_SESSION_DONE = "session_done"
EVENT_ERROR = "error"

_VALID_EVENTS = {
    EVENT_AGENT_TOKEN,
    EVENT_ACTION_PROPOSED,
    EVENT_ACTION_RESULT,
    EVENT_SESSION_DONE,
    EVENT_ERROR,
}

_sessions: dict[str, "ConversationSession"] = {}
_sessions_lock = threading.Lock()
_callbacks: dict[str, list[Callable[[str, dict], None]]] = {}
_callbacks_lock = threading.Lock()


class ConversationSession:
    """Mutable state for one active conversation."""

    def __init__(self, handle: str, autonomy_level: str, depth_level: str) -> None:
        self.handle = handle
        self.autonomy_level = autonomy_level
        self.depth_level = depth_level
        self._history: list[dict[str, Any]] = []
        self._pending_action: dict[str, Any] | None = None
        self._token_buffer: list[str] = []
        self._lock = threading.Lock()

    def append_message(self, role: str, text: str, *, metadata: dict | None = None) -> dict[str, Any]:
        entry: dict[str, Any] = {"role": role, "text": text, "metadata": metadata or {}}
        with self._lock:
            self._history.append(entry)
        return entry

    def history(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._history)

    def set_pending_action(self, action: dict[str, Any] | None) -> None:
        with self._lock:
            self._pending_action = action

    def pending_action(self) -> dict[str, Any] | None:
        with self._lock:
            return self._pending_action

    def append_token(self, token: str) -> None:
        with self._lock:
            self._token_buffer.append(token)

    def flush_tokens(self) -> str:
        """Return and clear the accumulated token buffer."""
        with self._lock:
            text = "".join(self._token_buffer)
            self._token_buffer.clear()
        return text


def _get_session(handle: str) -> ConversationSession:
    with _sessions_lock:
        session = _sessions.get(handle)
    if session is None:
        raise KeyError(f"No session with handle {handle!r}")
    return session


def _emit(handle: str, event_type: str, payload: dict[str, Any]) -> None:
    """Dispatch an event to all registered callbacks.

    Callbacks are called without holding any internal lock so they are safe
    to pass to GLib.idle_add or a queue.put without risk of deadlock.
    """
    if event_type not in _VALID_EVENTS:
        raise ValueError(f"Unknown event type: {event_type!r}")
    with _callbacks_lock:
        callbacks = list(_callbacks.get(handle, []))
    for cb in callbacks:
        cb(event_type, payload)


def start_session(*, project_control_path: Path | None = None) -> str:
    """Create a new conversation session and return its handle.

    Autonomy and depth levels are read from project-control.yaml once at
    session start and frozen for the session lifetime so in-flight behaviour
    is not disrupted by a YAML edit mid-conversation.
    """
    handle = f"conv-{uuid.uuid4().hex[:12]}"
    settings = autonomy_controls.load_autonomy_settings(project_control_path)
    session = ConversationSession(
        handle=handle,
        autonomy_level=settings["agent_autonomy_level"],
        depth_level=settings["agent_depth_level"],
    )
    with _sessions_lock:
        _sessions[handle] = session
    with _callbacks_lock:
        _callbacks[handle] = []
    return handle


def on_event(handle: str, callback: Callable[[str, dict], None]) -> None:
    """Register a callback to receive all events for a session.

    ``callback(event_type, payload)`` is called from whichever thread emits
    the event.  For GTK callers wrap in GLib.idle_add; for background workers
    route through a queue.
    """
    with _callbacks_lock:
        if handle not in _callbacks:
            raise KeyError(f"No session with handle {handle!r}")
        _callbacks[handle].append(callback)


def submit_message(handle: str, text: str) -> None:
    """Record a user message and emit session_done.

    Chunk 23 stub: no model call is made yet.  Streaming and model calls are
    wired in Chunks 25 (greeting) and 28 (streaming responses).
    """
    session = _get_session(handle)
    if not text or not text.strip():
        _emit(handle, EVENT_ERROR, {"handle": handle, "error": "message text is empty"})
        return
    entry = session.append_message("user", text.strip())
    _emit(handle, EVENT_SESSION_DONE, {"handle": handle, "message": entry})


def emit_token(handle: str, token: str) -> None:
    """Append a streaming token to the session buffer and emit agent_token.

    Called by the model streaming layer added in Chunk 28.  Safe from any thread.
    """
    session = _get_session(handle)
    session.append_token(token)
    _emit(handle, EVENT_AGENT_TOKEN, {"handle": handle, "token": token})


def propose_action(handle: str, action: dict[str, Any]) -> None:
    """Record a proposed action and emit action_proposed.

    Suppressed at autonomy level A0: the action is not shown to the user.
    An error event is emitted instead to inform the caller.
    """
    session = _get_session(handle)
    if session.autonomy_level == "A0":
        _emit(
            handle,
            EVENT_ERROR,
            {
                "handle": handle,
                "error": "action execution disabled at A0; set agent_autonomy_level to A1 or higher",
                "action_id": action.get("id"),
            },
        )
        return
    session.set_pending_action(action)
    _emit(handle, EVENT_ACTION_PROPOSED, {"handle": handle, "action": action})


def record_action_result(handle: str, result: dict[str, Any]) -> None:
    """Clear the pending action and emit action_result."""
    session = _get_session(handle)
    session.set_pending_action(None)
    _emit(handle, EVENT_ACTION_RESULT, {"handle": handle, "result": result})


def end_session(handle: str) -> None:
    """Remove a session from the registry.  Silent if the handle is unknown."""
    with _sessions_lock:
        _sessions.pop(handle, None)
    with _callbacks_lock:
        _callbacks.pop(handle, None)


def session_info(handle: str) -> dict[str, Any]:
    """Return a snapshot of session state."""
    session = _get_session(handle)
    return {
        "handle": session.handle,
        "autonomy_level": session.autonomy_level,
        "depth_level": session.depth_level,
        "history_length": len(session.history()),
        "pending_action": session.pending_action(),
    }


# ---------------------------------------------------------------------------
# Greeting generator (pure — no I/O, no GTK dependency)
# ---------------------------------------------------------------------------

def _open_question_for_findings(findings: list[dict[str, Any]]) -> str:
    """Pick the most relevant follow-up question for a set of urgent findings."""
    ids = {f.get("id", "") for f in findings}
    if any(fid.startswith("disk-") for fid in ids):
        return "Want to start with the disk space situation?"
    if "memory-pressure" in ids:
        return "Should we take a closer look at memory usage first?"
    if "failed-services" in ids:
        return "Want to investigate the failed services?"
    if "journal-errors" in ids:
        return "Should we look at the critical log entries together?"
    if "network-basics" in ids:
        return "Want to check what the network evidence says?"
    if "package-manager-health" in ids:
        return "Want me to walk through the package manager issue?"
    return "Where would you like to start?"


def generate_greeting(diagnostic_report: dict[str, Any] | None) -> str:
    """Map a completed diagnostic report to an opening greeting string.

    Four states:
      partial   — report is None or contains an ``error`` key
      healthy   — no warning/critical findings
      findings  — one or more warning/critical findings (brief summary + open question)

    The ``loading`` state ("Checking your machine…") is emitted by
    ``launch_diagnostic_greeting`` before the background thread starts; it is
    not returned by this function.
    """
    if not diagnostic_report or "error" in diagnostic_report:
        return GREETING_PARTIAL_FAILURE

    findings = diagnostic_report.get("findings", [])
    urgent = [f for f in findings if f.get("severity") in {"critical", "warning"}]

    if not urgent:
        return GREETING_HEALTHY

    count = len(urgent)
    titles = [f.get("title") or f.get("id") or "finding" for f in urgent[:3]]
    summary = ", ".join(titles)
    if count > 3:
        summary += f", and {count - 3} more"

    question = _open_question_for_findings(urgent)
    noun = "item" if count == 1 else "items"
    return f"I found {count} {noun} worth your attention: {summary}.\n\n{question}"


def launch_diagnostic_greeting(
    handle: str,
    *,
    collect_fn: Callable[[], dict[str, Any]] | None = None,
    on_loading: Callable[[str], None] | None = None,
) -> None:
    """Trigger diagnostic collection in a background thread and emit a greeting.

    ``collect_fn`` is injectable for tests; when omitted, ``collect_diagnostics``
    is imported lazily so there is no circular import at module load time.

    ``on_loading`` is called synchronously on the caller's thread before the
    background thread starts — use it to update a status label.  For GTK callers
    the callback is already on the main thread; no ``GLib.idle_add`` needed there.

    The greeting is recorded in session history and emitted as:
      - one ``agent_token`` event (the full greeting text as a single token)
      - one ``session_done`` event with a ``greeting`` key
    """
    if on_loading is not None:
        on_loading(GREETING_LOADING)

    def _worker() -> None:
        try:
            if collect_fn is not None:
                report: dict[str, Any] = collect_fn()
            else:
                from .diagnostics import collect_diagnostics  # lazy — avoids circular import
                report = collect_diagnostics()
        except Exception as exc:
            report = {"error": str(exc)}

        greeting = generate_greeting(report)
        session = _get_session(handle)
        session.append_message("agent", greeting, metadata={"source": "diagnostic-greeting"})
        _emit(handle, EVENT_AGENT_TOKEN, {"handle": handle, "token": greeting})
        _emit(handle, EVENT_SESSION_DONE, {"handle": handle, "greeting": greeting})

    threading.Thread(target=_worker, daemon=True).start()
