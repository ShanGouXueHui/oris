from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import unquote, urlparse

from dev_employee_runtime.intake_config import CATALOG_DIR, DEFAULT_HOST, DEFAULT_PORT, auth_ok, json_response, registry
from dev_employee_runtime.intake_goal import create_goal
from dev_employee_runtime.intake_status import list_goals, task_status


class Handler(BaseHTTPRequestHandler):
    server_version = "oris-dev-employee-intake/0.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"{self.address_string()} - {fmt % args}", flush=True)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/health":
            return json_response(self, 200, {"status": "ok", "service": "dev_employee_intake_api"})
        if path == "/projects":
            projects = registry().get("projects", {})
            return json_response(self, 200, {"projects": sorted(projects.keys())})
        if path == "/goals":
            return json_response(self, 200, list_goals())
        if path.startswith("/goals/"):
            task_id = unquote(path.removeprefix("/goals/")).strip()
            try:
                return json_response(self, 200, task_status(task_id))
            except Exception as exc:
                return json_response(self, 400, {"error": type(exc).__name__, "message": str(exc)})
        return json_response(self, 404, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path != "/goals":
            return json_response(self, 404, {"error": "not_found"})
        if not auth_ok(self):
            return json_response(self, 401, {"error": "unauthorized"})
        try:
            length = int(self.headers.get("Content-Length") or "0")
            if length <= 0 or length > 80_000:
                return json_response(self, 400, {"error": "invalid_body_length"})
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            result = create_goal(payload)
            status = 201 if result.get("status") == "queued" else 502
            return json_response(self, status, result)
        except Exception as exc:
            return json_response(self, 400, {"error": type(exc).__name__, "message": str(exc)})


def main() -> int:
    host = os.environ.get("ORIS_DEV_EMPLOYEE_INTAKE_HOST", DEFAULT_HOST)
    port = int(os.environ.get("ORIS_DEV_EMPLOYEE_INTAKE_PORT", str(DEFAULT_PORT)))
    if host not in {"127.0.0.1", "localhost"}:
        raise SystemExit("Refusing to bind non-loopback host")
    CATALOG_DIR.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"ORIS intake API listening on http://{host}:{port}", flush=True)
    server.serve_forever()
    return 0
