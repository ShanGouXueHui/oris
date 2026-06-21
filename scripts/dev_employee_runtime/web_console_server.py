from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import unquote, urlparse

from dev_employee_runtime.web_console_config import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    WEB_CONSOLE_AUDIT_DIR,
    allowed_projects,
    console_auth_ok,
    filter_projects,
    html_response,
    intake_request,
    json_response,
    submit_enabled,
    write_audit_event,
)
from dev_employee_runtime.web_console_page import page


class Handler(BaseHTTPRequestHandler):
    server_version = "oris-dev-employee-console/0.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"{self.address_string()} - {fmt % args}", flush=True)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        write_audit_event(self, {"event": "get", "path": path})
        if path in {"/", "/index.html"}:
            return html_response(self, 200, page())
        if path == "/api/projects":
            status, body = intake_request("GET", "/projects")
            return json_response(self, status, filter_projects(body))
        if path == "/api/goals":
            status, body = intake_request("GET", "/goals")
            return json_response(self, status, body)
        if path.startswith("/api/goals/"):
            task_id = unquote(path.removeprefix("/api/goals/")).strip()
            status, body = intake_request("GET", "/goals/" + task_id)
            return json_response(self, status, body)
        return json_response(self, 404, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        write_audit_event(self, {"event": "post", "path": path})
        if path != "/api/goals":
            return json_response(self, 404, {"error": "not_found"})
        if not submit_enabled():
            return json_response(self, 403, {"error": "submit_disabled"})
        if not console_auth_ok(self):
            return json_response(self, 401, {"error": "unauthorized"})
        try:
            length = int(self.headers.get("Content-Length") or "0")
            if length <= 0 or length > 80_000:
                return json_response(self, 400, {"error": "invalid_body_length"})
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            project_key = str(payload.get("project_key") or "")
            if allowed_projects() and project_key not in allowed_projects():
                return json_response(self, 403, {"error": "project_not_allowed"})
            status, body = intake_request("POST", "/goals", payload, auth=True)
            return json_response(self, status, body)
        except Exception as exc:
            write_audit_event(self, {"event": "post_error", "error_type": type(exc).__name__})
            return json_response(self, 400, {"error": type(exc).__name__, "message": str(exc)})


def main() -> int:
    host = os.environ.get("ORIS_DEV_EMPLOYEE_WEB_CONSOLE_HOST", DEFAULT_HOST)
    port = int(os.environ.get("ORIS_DEV_EMPLOYEE_WEB_CONSOLE_PORT", str(DEFAULT_PORT)))
    if host not in {"127.0.0.1", "localhost"}:
        raise SystemExit("Refusing to bind non-loopback host")
    WEB_CONSOLE_AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"ORIS Web Console listening on http://{host}:{port}", flush=True)
    server.serve_forever()
    return 0
