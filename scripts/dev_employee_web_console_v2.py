#!/usr/bin/env python3
"""ORIS Dev Employee Web Console v2.

The console remains a thin authenticated UI/proxy. It adds task cancellation and
explicit retry controls, while all lifecycle policy and queue mutation stays in
the loopback intake API v2.
"""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import unquote, urlparse

import dev_employee_web_console as v1

DEFAULT_HOST = v1.DEFAULT_HOST
DEFAULT_PORT = v1.DEFAULT_PORT


def page() -> str:
    content = v1.page()
    old_buttons = '''          <button onclick="loadStatus()">Load status</button>
        </div>
      </div>
      <div id="summary"></div>
'''
    new_buttons = '''          <button onclick="loadStatus()">Load status</button>
          <button class="secondary" onclick="cancelGoal()">Cancel task</button>
          <button class="secondary" onclick="retryGoal()">Retry terminal task</button>
        </div>
      </div>
      <div class="muted">Cancel is accepted only before commit/push. Retry always creates or reuses a new task ID.</div>
      <div id="summary"></div>
'''
    if old_buttons not in content:
        raise RuntimeError("unable to inject lifecycle buttons into Web Console page")
    content = content.replace(old_buttons, new_buttons, 1)

    old_script = '''const tokenInput = document.getElementById('console_token');
'''
    new_script = '''async function cancelGoal() {
  const taskId = document.getElementById('lookup_task_id').value.trim();
  if (!taskId) {
    document.getElementById('status_result').textContent = 'Task ID is required.';
    return;
  }
  rememberToken();
  const reason = window.prompt('Cancellation reason', 'Operator requested cancellation');
  if (reason === null) return;
  try {
    const data = await api('/api/goals/' + encodeURIComponent(taskId) + '/cancel', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({reason})
    });
    renderSummary(data.current_status || data);
    document.getElementById('status_result').textContent = JSON.stringify(data, null, 2);
  } catch (error) {
    document.getElementById('status_result').textContent = `Cancel failed:\n${String(error)}`;
  }
}
async function retryGoal() {
  const taskId = document.getElementById('lookup_task_id').value.trim();
  if (!taskId) {
    document.getElementById('status_result').textContent = 'Task ID is required.';
    return;
  }
  rememberToken();
  const reason = window.prompt('Retry reason', 'Explicit operator retry');
  if (reason === null) return;
  try {
    const data = await api('/api/goals/' + encodeURIComponent(taskId) + '/retry', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({reason})
    });
    if (data.task_id) document.getElementById('lookup_task_id').value = data.task_id;
    document.getElementById('status_result').textContent = JSON.stringify(data, null, 2);
    if (data.current_status) renderSummary(data.current_status);
  } catch (error) {
    document.getElementById('status_result').textContent = `Retry failed:\n${String(error)}`;
  }
}
const tokenInput = document.getElementById('console_token');
'''
    if old_script not in content:
        raise RuntimeError("unable to inject lifecycle JavaScript into Web Console page")
    return content.replace(old_script, new_script, 1)


def read_body(handler: BaseHTTPRequestHandler, max_length: int = 80_000) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length") or "0")
    if length == 0:
        return {}
    if length < 0 or length > max_length:
        raise ValueError("invalid_body_length")
    payload = json.loads(handler.rfile.read(length).decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("body must be a JSON object")
    return payload


class Handler(BaseHTTPRequestHandler):
    server_version = "oris-dev-employee-web-console/0.2"

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"{self.address_string()} - {fmt % args}", flush=True)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path in {"/", "/index.html"}:
            return v1.html_response(self, 200, page())
        if path == "/health":
            return v1.json_response(
                self,
                200,
                {
                    "status": "ok",
                    "service": "dev_employee_web_console_v2",
                    "lifecycle_controls": ["cancel", "retry"],
                },
            )
        if path == "/api/projects":
            if not v1.console_auth_ok(self):
                return v1.json_response(self, 401, {"error": "unauthorized"})
            status, body = v1.intake_request("GET", "/projects")
            return v1.json_response(self, status, v1.filter_projects(body))
        if path == "/api/goals":
            if not v1.console_auth_ok(self):
                return v1.json_response(self, 401, {"error": "unauthorized"})
            status, body = v1.intake_request("GET", "/goals")
            return v1.json_response(self, status, body)
        if path.startswith("/api/goals/"):
            if not v1.console_auth_ok(self):
                return v1.json_response(self, 401, {"error": "unauthorized"})
            task_id = unquote(path.removeprefix("/api/goals/"))
            status, body = v1.intake_request("GET", f"/goals/{task_id}")
            return v1.json_response(self, status, body)
        return v1.json_response(self, 404, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if not v1.console_auth_ok(self):
            v1.write_audit_event(self, {"action": "lifecycle_mutation", "result": "rejected", "reason": "unauthorized"})
            return v1.json_response(self, 401, {"error": "unauthorized"})
        if not v1.submit_enabled():
            v1.write_audit_event(self, {"action": "lifecycle_mutation", "result": "rejected", "reason": "submit_disabled"})
            return v1.json_response(self, 403, {"error": "submit_disabled"})
        try:
            if path == "/api/goals":
                payload = read_body(self)
                project_key = str(payload.get("project_key") or "")
                task_id = str(payload.get("task_id") or "")
                objective = str(payload.get("objective") or "")
                if project_key not in v1.allowed_projects():
                    v1.write_audit_event(
                        self,
                        {
                            "action": "submit_goal",
                            "result": "rejected",
                            "reason": "project_not_allowed",
                            "project_key": project_key,
                            "task_id": task_id,
                        },
                    )
                    return v1.json_response(self, 403, {"error": "project_not_allowed", "project_key": project_key})
                status, body = v1.intake_request("POST", "/goals", body=payload, auth=True)
                v1.write_audit_event(
                    self,
                    {
                        "action": "submit_goal",
                        "result": "submitted" if 200 <= status < 300 else "upstream_error",
                        "upstream_status": status,
                        "project_key": project_key,
                        "task_id": task_id or (body.get("task_id") if isinstance(body, dict) else None),
                        "objective_length": len(objective),
                    },
                )
                return v1.json_response(self, status, body)

            for action in ["cancel", "retry"]:
                suffix = f"/{action}"
                if path.startswith("/api/goals/") and path.endswith(suffix):
                    task_id = unquote(path.removeprefix("/api/goals/").removesuffix(suffix)).strip("/")
                    payload = read_body(self, max_length=20_000)
                    payload.setdefault("requested_by", "public-web-console")
                    status, body = v1.intake_request(
                        "POST",
                        f"/goals/{task_id}/{action}",
                        body=payload,
                        auth=True,
                    )
                    v1.write_audit_event(
                        self,
                        {
                            "action": action,
                            "result": "accepted" if 200 <= status < 300 else "upstream_error",
                            "upstream_status": status,
                            "task_id": task_id,
                            "reason_length": len(str(payload.get("reason") or "")),
                        },
                    )
                    return v1.json_response(self, status, body)
            return v1.json_response(self, 404, {"error": "not_found"})
        except Exception as exc:
            v1.write_audit_event(
                self,
                {
                    "action": "lifecycle_mutation",
                    "result": "error",
                    "reason": type(exc).__name__,
                },
            )
            return v1.json_response(self, 400, {"error": type(exc).__name__, "message": str(exc)})


def main() -> int:
    host = os.environ.get("ORIS_DEV_EMPLOYEE_WEB_CONSOLE_HOST", DEFAULT_HOST)
    port = int(os.environ.get("ORIS_DEV_EMPLOYEE_WEB_CONSOLE_PORT", str(DEFAULT_PORT)))
    if host not in {"127.0.0.1", "localhost"}:
        raise SystemExit("Refusing to bind non-loopback host")
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"ORIS Dev Employee Web Console v2 listening on http://{host}:{port}", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
