"""Local web server that exposes the stack review GUI and JSON API."""

from __future__ import annotations

from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import socket
import threading
import webbrowser

from .agents import build_agents
from .ai_engine import answer_question
from .diagnostics import collect_diagnostics
from .maintenance_reporting import generate_maintenance_report
from .reporting import generate_report
from .request_plans import prepare_request_plan
from .scanner import map_filesystem, suggest_roots


WEB_ROOT = Path(__file__).resolve().parent / "web"


def build_report() -> dict:
    results = [agent.run() for agent in build_agents()]
    return generate_report(results)


def build_maintenance_report() -> dict:
    return generate_maintenance_report(collect_diagnostics())


class StackCoachHandler(SimpleHTTPRequestHandler):
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
        if self.path == "/health":
            self.send_response(HTTPStatus.OK)
            self.end_headers()
            self.wfile.write(b"ok")
            return
        super().do_GET()

    def do_POST(self) -> None:
        if self.path not in {"/api/map", "/api/request-plan", "/api/ask"}:
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
            self._send_json(
                prepare_request_plan(
                    request_text,
                    os_name=str(os_name) if os_name else None,
                    distribution_hint=str(desktop_hint) if desktop_hint else None,
                )
            )
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
    server = ThreadingHTTPServer((host, active_port), StackCoachHandler)
    url = f"http://{host}:{active_port}"

    if open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    print(f"System Stack Review and Coach running at {url}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
