"""Local web server that exposes the System Coach browser GUI and JSON API."""

from __future__ import annotations

import datetime as dt
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import socket
import threading
import webbrowser

from .agents import build_agents
from .action_plan_registry import execute_registered_action, register_action_plan
from .ai_engine import answer_question, reason_about_request
from .diagnostics import collect_diagnostics
from .maintenance_actions import build_action_contract
from .maintenance_history import load_history, record_maintenance_report, record_request_plan
from .maintenance_history import record_action_result
from .maintenance_reporting import generate_maintenance_report
from .pop_cosmic_actions import prepare_pop_cosmic_action, prepare_verification_plan
from .pop_cosmic_brain import analyze_pop_cosmic_issue
from .pop_cosmic_controls import load_pop_cosmic_controls
from .pop_cosmic_deep_scan import run_pop_cosmic_deep_scan
from .pop_cosmic_knowledge import load_relevant_lessons, load_relevant_research, save_lesson, save_research_records, make_lesson
from .pop_cosmic_profile import detect_pop_cosmic_environment
from .pop_cosmic_research import research_pop_cosmic_issue
from .reporting import generate_report
from .request_evidence import collect_request_evidence
from .request_plans import prepare_request_plan
from .scanner import map_filesystem, suggest_roots


WEB_ROOT = Path(__file__).resolve().parent / "web"


def build_report() -> dict:
    results = [agent.run() for agent in build_agents()]
    return generate_report(results)


def build_maintenance_report() -> dict:
    report = generate_maintenance_report(collect_diagnostics())
    report["action_plans"] = [register_action_plan(plan) for plan in report.get("action_plans", [])]
    record_maintenance_report(report)
    return report


def _blocked_execution_request(error: str, server_plan_id: str | None = None) -> dict:
    now = dt.datetime.now().isoformat(timespec="seconds")
    return {
        "action_id": None,
        "plan_id": None,
        "server_plan_id": server_plan_id,
        "status": "blocked",
        "started_at": now,
        "finished_at": now,
        "execution_enabled": False,
        "exit_code": None,
        "commands": [],
        "output": "",
        "error": error,
        "post_check": [],
        "rollback": [],
    }


class SystemCoachHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_ROOT), **kwargs)

    def _send_json(self, payload: dict, status: int = HTTPStatus.OK) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        if self.path == "/api/report":
            self._send_json(build_report())
            return
        if self.path == "/api/scan-options":
            self._send_json({"suggested_roots": suggest_roots()})
            return
        if self.path == "/api/maintenance":
            self._send_json(build_maintenance_report())
            return
        if self.path == "/api/history":
            self._send_json(load_history())
            return
        if self.path == "/api/pop-cosmic/profile":
            self._send_json(detect_pop_cosmic_environment())
            return
        if self.path == "/health":
            self.send_response(HTTPStatus.OK)
            self.end_headers()
            self.wfile.write(b"ok")
            return
        super().do_GET()

    def do_POST(self) -> None:
        if self.path not in {
            "/api/map",
            "/api/request-plan",
            "/api/action-contract",
            "/api/action-run",
            "/api/ask",
            "/api/pop-cosmic/deep-scan",
            "/api/pop-cosmic/research",
            "/api/pop-cosmic/analyze",
            "/api/pop-cosmic/plan",
            "/api/pop-cosmic/execute",
            "/api/pop-cosmic/verify",
        }:
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(content_length)
            payload = json.loads(raw_body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self.send_error(HTTPStatus.BAD_REQUEST, "Invalid JSON payload")
            return

        if self.path == "/api/request-plan":
            request_text = str(payload.get("request", ""))
            os_name = payload.get("os_name")
            desktop_hint = payload.get("desktop_hint")
            maintenance_report = payload.get("maintenance_report")
            evidence = collect_request_evidence(
                request_text,
                os_name=str(os_name) if os_name else None,
                desktop_hint=str(desktop_hint) if desktop_hint else None,
            )
            reasoning = reason_about_request(
                request_text,
                os_name=str(os_name) if os_name else None,
                desktop_hint=str(desktop_hint) if desktop_hint else None,
                maintenance_report=maintenance_report if isinstance(maintenance_report, dict) else None,
                request_evidence=evidence,
            )
            reasoning["request_evidence"] = evidence
            if not reasoning.get("ok"):
                reasoning = {
                    "source": "deterministic-fallback",
                    "model": None,
                    "family": None,
                    "ready": True,
                    "confidence": None,
                    "reasoning_summary": reasoning.get("reasoning_summary", ""),
                    "request_evidence": evidence,
                }
            plan = prepare_request_plan(
                request_text,
                os_name=str(os_name) if os_name else None,
                distribution_hint=str(desktop_hint) if desktop_hint else None,
                family_override=reasoning.get("family"),
                reasoning=reasoning,
            )
            plan = register_action_plan(plan)
            record_request_plan(plan)
            self._send_json(plan)
            return

        if self.path == "/api/action-contract":
            plan = payload.get("plan")
            if not isinstance(plan, dict):
                self.send_error(HTTPStatus.BAD_REQUEST, "plan must be an object")
                return
            self._send_json(build_action_contract(plan))
            return

        if self.path == "/api/action-run":
            server_plan_id = str(payload.get("plan_id", "")).strip()
            if not server_plan_id:
                result = _blocked_execution_request("execution requires a server-side plan_id")
                record_action_result(result)
                self._send_json(result, HTTPStatus.BAD_REQUEST)
                return
            result = execute_registered_action(server_plan_id, str(payload.get("confirmation_text", "")))
            record_action_result(result)
            self._send_json(result)
            return

        if self.path == "/api/pop-cosmic/deep-scan":
            scope = str(payload.get("scope", "standard"))
            self._send_json(run_pop_cosmic_deep_scan(scope))
            return

        if self.path == "/api/pop-cosmic/research":
            symptom = str(payload.get("symptom", ""))
            profile = payload.get("profile") if isinstance(payload.get("profile"), dict) else detect_pop_cosmic_environment()
            controls = load_pop_cosmic_controls()
            requested_live_web = bool(payload.get("enabled", False))
            effective_live_web = bool(controls.get("web_research_enabled")) and requested_live_web
            governance = {
                "source": controls.get("source"),
                "web_research_enabled": bool(controls.get("web_research_enabled")),
                "requested_live_web": requested_live_web,
                "effective_live_web": effective_live_web,
                "allowed_domains": controls.get("allowed_domains", []),
                "reason": controls.get("governance_reason", ""),
            }
            if requested_live_web and not effective_live_web:
                governance["reason"] = (
                    "Live Pop/COSMIC web research was requested, but project controls keep it disabled. "
                    "Returning local/manual records and official source metadata only."
                )
            elif controls.get("web_research_enabled") and not requested_live_web:
                governance["reason"] = (
                    "Project controls allow live Pop/COSMIC web research, but this request did not opt in. "
                    "Returning local/manual records and official source metadata only."
                )
            research = research_pop_cosmic_issue(
                symptom,
                profile,
                enabled=effective_live_web,
                include_github=bool(payload.get("include_github", False)) and effective_live_web,
                manual_notes=str(payload.get("manual_notes", "")),
                max_results=int(controls.get("max_results_per_query", 8)),
                governance=governance,
            )
            save_research_records(research.get("records", []))
            self._send_json(research)
            return

        if self.path == "/api/pop-cosmic/analyze":
            symptom = str(payload.get("symptom", ""))
            scan = payload.get("scan") if isinstance(payload.get("scan"), dict) else run_pop_cosmic_deep_scan("standard")
            profile = scan.get("profile", {})
            research = payload.get("research") if isinstance(payload.get("research"), list) else load_relevant_research(symptom, profile)
            lessons = load_relevant_lessons(symptom, profile)
            self._send_json(analyze_pop_cosmic_issue(symptom, scan, research, lessons))
            return

        if self.path == "/api/pop-cosmic/plan":
            action_key = str(payload.get("action_key", "deep-scan-standard"))
            analysis = payload.get("analysis") if isinstance(payload.get("analysis"), dict) else {}
            scan = payload.get("scan") if isinstance(payload.get("scan"), dict) else {}
            plan = prepare_pop_cosmic_action(action_key, analysis, scan)
            plan = register_action_plan(plan)
            record_request_plan(plan)
            self._send_json(plan)
            return

        if self.path == "/api/pop-cosmic/execute":
            server_plan_id = str(payload.get("plan_id", "")).strip()
            if not server_plan_id:
                result = _blocked_execution_request("execution requires a server-side plan_id")
                record_action_result(result)
                self._send_json(result, HTTPStatus.BAD_REQUEST)
                return
            result = execute_registered_action(server_plan_id, str(payload.get("confirmation_text", "")))
            record_action_result(result)
            self._send_json(result)
            return

        if self.path == "/api/pop-cosmic/verify":
            result = payload.get("result") if isinstance(payload.get("result"), dict) else {}
            original_scan = payload.get("scan") if isinstance(payload.get("scan"), dict) else {}
            post_scan = prepare_verification_plan(result, original_scan)
            profile = post_scan.get("profile", {})
            lesson = make_lesson(
                symptom=str(payload.get("symptom", "")),
                profile=profile,
                evidence_summary="; ".join(item.get("summary", "") for item in post_scan.get("findings", [])[:4]),
                action_taken=", ".join(result.get("commands", [])),
                result="improved" if result.get("status") == "completed" else "unknown",
                verification="Post-scan collected after Pop/COSMIC action.",
            )
            save_lesson(lesson)
            self._send_json({"post_scan": post_scan, "lesson": lesson})
            return

        if self.path == "/api/ask":
            question = str(payload.get("question", ""))
            response = answer_question(
                question,
                payload.get("report"),
                payload.get("system_map"),
                payload.get("maintenance_report"),
                payload.get("request_plan"),
            )
            self._send_json(response)
            return

        roots = payload.get("roots", [])
        if not isinstance(roots, list):
            self.send_error(HTTPStatus.BAD_REQUEST, "roots must be a list of paths")
            return

        report = map_filesystem([str(item) for item in roots])
        self._send_json(report)


def _find_open_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def serve(host: str = "127.0.0.1", port: int | None = None, open_browser: bool = True) -> None:
    active_port = port or _find_open_port()
    server = ThreadingHTTPServer((host, active_port), SystemCoachHandler)
    url = f"http://{host}:{active_port}"

    if open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    print(f"System Coach and Maintenance Manager running at {url}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
