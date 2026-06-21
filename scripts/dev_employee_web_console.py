#!/usr/bin/env python3
"""Local-only Web console prototype for ORIS Dev Employee.

The console is a thin UI layer over the already verified intake/status service.
It binds to loopback only, does not invoke Codex directly, does not mutate queue
files directly, and does not push GitHub. It submits goals through the local
intake API and displays Web-friendly GitHub evidence from status responses.
"""

from __future__ import annotations

import html
import json
import os
import urllib.error as urlerror
import urllib.request as urlrequest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from dev_employee_runtime.clock import now_iso
from dev_employee_runtime.env import load_env
from dev_employee_runtime.net import require_loopback_url
from dev_employee_runtime.paths import discover_repo_root
from dev_employee_runtime.settings import load_runtime_settings

ORIS_DIR = discover_repo_root()
RUNTIME_SETTINGS = load_runtime_settings(ORIS_DIR)
DEFAULT_HOST = RUNTIME_SETTINGS.web_console_host
DEFAULT_PORT = RUNTIME_SETTINGS.web_console_port
DEFAULT_INTAKE_URL = RUNTIME_SETTINGS.intake_url
WEB_CONSOLE_AUDIT_DIR = ORIS_DIR / "logs" / "dev_employee" / "web_console_audit"
DEFAULT_ENV_FILE = Path.home() / ".config" / "oris" / "dev_employee_enqueue.env"
INTAKE_TOKEN_KEY = "ORIS_DEV_EMPLOYEE_INTAKE_TOKEN"
CONSOLE_TOKEN_KEY = "ORIS_DEV_EMPLOYEE_WEB_CONSOLE_TOKEN"
CONSOLE_AUTH_HEADER = "X-ORIS-Console-Token"
AUTH_HEADER = "X-ORIS-Token"


def audit_path() -> Path:
    stamp = now_iso()[:10].replace("-", "")
    return WEB_CONSOLE_AUDIT_DIR / f"web_console_audit_{stamp}.jsonl"


def write_audit_event(handler: BaseHTTPRequestHandler, event: dict[str, Any]) -> None:
    safe = {
        "ts": now_iso(),
        "remote_addr": handler.client_address[0] if handler.client_address else None,
        "method": handler.command,
        "path": handler.path,
        **event,
    }
    # Never persist token/header values.
    for forbidden in ["token", "headers", "authorization", "x_oris_console_token", "x-oris-console-token"]:
        safe.pop(forbidden, None)
    path = audit_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(safe, ensure_ascii=False, sort_keys=True) + "\n")


def intake_base_url() -> str:
    url = os.environ.get("ORIS_DEV_EMPLOYEE_INTAKE_URL", DEFAULT_INTAKE_URL).rstrip("/")
    require_loopback_url(url)
    return url


def intake_token() -> str:
    token = os.environ.get(INTAKE_TOKEN_KEY) or load_env(DEFAULT_ENV_FILE).get(INTAKE_TOKEN_KEY)
    if not token:
        raise RuntimeError(f"{INTAKE_TOKEN_KEY} missing from environment or local config")
    return token


def console_token() -> str:
    token = os.environ.get(CONSOLE_TOKEN_KEY) or load_env(DEFAULT_ENV_FILE).get(CONSOLE_TOKEN_KEY)
    if not token:
        raise RuntimeError(f"{CONSOLE_TOKEN_KEY} missing from environment or local config")
    return token


def console_auth_ok(handler: BaseHTTPRequestHandler) -> bool:
    return (handler.headers.get(CONSOLE_AUTH_HEADER) or "") == console_token()


def allowed_projects() -> set[str]:
    raw = os.environ.get("ORIS_DEV_EMPLOYEE_WEB_CONSOLE_PROJECT_ALLOWLIST", "")
    return {item.strip() for item in raw.split(",") if item.strip()}


def submit_enabled() -> bool:
    return os.environ.get("ORIS_DEV_EMPLOYEE_WEB_CONSOLE_SUBMIT_ENABLED", "0").lower() in {"1", "true", "yes", "on"}


def filter_projects(body: Any) -> Any:
    if not isinstance(body, dict):
        return body
    projects = body.get("projects")
    if not isinstance(projects, list):
        return body
    allow = allowed_projects()
    return body if not allow else {**body, "projects": [item for item in projects if item in allow]}


def json_response(handler: BaseHTTPRequestHandler, status: int, payload: Any) -> None:
    body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def html_response(handler: BaseHTTPRequestHandler, status: int, content: str) -> None:
    body = content.encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def intake_request(method: str, path: str, body: dict[str, Any] | None = None, auth: bool = False) -> tuple[int, Any]:
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    headers = {"Content-Type": "application/json"}
    if auth:
        headers[AUTH_HEADER] = intake_token()
    req = urlrequest.Request(intake_base_url() + path, data=data, method=method, headers=headers)
    try:
        with urlrequest.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urlerror.HTTPError as exc:
        text = exc.read().decode("utf-8")
        try:
            return exc.code, json.loads(text)
        except json.JSONDecodeError:
            return exc.code, {"raw": text}
    except urlerror.URLError as exc:
        return 599, {"error": "url_error", "message": str(exc)}


def page() -> str:
    return """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>ORIS Dev Employee Console</title>
  <style>
    body { font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 0; background: #f6f7fb; color: #1f2937; }
    header { background: #111827; color: white; padding: 18px 24px; }
    main { max-width: 1180px; margin: 0 auto; padding: 24px; }
    section { background: white; border-radius: 14px; box-shadow: 0 1px 4px rgba(15, 23, 42, 0.08); padding: 20px; margin-bottom: 18px; }
    label { display: block; font-weight: 650; margin: 12px 0 6px; }
    input, select, textarea { width: 100%; box-sizing: border-box; padding: 10px 12px; border: 1px solid #cbd5e1; border-radius: 10px; font: inherit; }
    textarea { min-height: 150px; }
    button { border: 0; border-radius: 10px; padding: 10px 14px; background: #2563eb; color: white; font-weight: 700; cursor: pointer; margin-right: 8px; }
    button.secondary { background: #64748b; }
    button.danger { background: #b91c1c; }
    pre { background: #0f172a; color: #d1fae5; padding: 14px; border-radius: 10px; overflow-x: auto; white-space: pre-wrap; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 14px; }
    .muted { color: #64748b; font-size: 0.94rem; }
    .pill { display: inline-block; padding: 3px 8px; border-radius: 999px; background: #e0f2fe; color: #075985; font-size: 0.82rem; margin-left: 6px; }
  </style>
</head>
<body>
  <header><h1>ORIS Dev Employee Console <span class="pill">local only</span></h1></header>
  <main>
    <section>
      <h2>Submit a governed development goal</h2>
      <p class="muted">Submission is disabled unless ORIS_DEV_EMPLOYEE_WEB_CONSOLE_SUBMIT_ENABLED=1. The console forwards to the loopback intake API; it does not invoke Codex or mutate repositories directly.</p>
      <div class="grid">
        <div><label>Project</label><select id="project"></select></div>
        <div><label>Optional task id</label><input id="taskId" placeholder="goal-project-YYYYMMDD-HHMMSS" /></div>
      </div>
      <label>Objective</label><textarea id="objective" placeholder="Describe the concrete product outcome, constraints, and acceptance checks..."></textarea>
      <label>Constraints, one per line</label><textarea id="constraints" placeholder="No production changes&#10;Preserve existing tests"></textarea>
      <label>Expected checks, one per line</label><textarea id="checks" placeholder="pytest&#10;python -m compileall"></textarea>
      <label>Commit message</label><input id="commitMessage" placeholder="feat: implement ..." />
      <label>Console token</label><input id="consoleToken" type="password" placeholder="X-ORIS-Console-Token" />
      <button onclick="submitGoal()">Submit goal</button>
      <button class="secondary" onclick="refreshGoals()">Refresh goals</button>
    </section>
    <section>
      <h2>Goals</h2>
      <div id="goals"></div>
    </section>
    <section>
      <h2>Status / evidence</h2>
      <pre id="output">Ready.</pre>
    </section>
  </main>
<script>
function lines(id) { return document.getElementById(id).value.split('\n').map(x => x.trim()).filter(Boolean); }
function show(x) { document.getElementById('output').textContent = typeof x === 'string' ? x : JSON.stringify(x, null, 2); }
async function api(path, opts={}) {
  const resp = await fetch(path, opts);
  const text = await resp.text();
  try { return {status: resp.status, body: JSON.parse(text)}; } catch { return {status: resp.status, body: text}; }
}
async function loadProjects() {
  const r = await api('/api/projects');
  const select = document.getElementById('project');
  select.innerHTML = '';
  const projects = (r.body && r.body.projects) || [];
  for (const project of projects) {
    const option = document.createElement('option');
    option.value = project;
    option.textContent = project;
    select.appendChild(option);
  }
}
async function refreshGoals() {
  const r = await api('/api/goals');
  const div = document.getElementById('goals');
  const items = (r.body && r.body.items) || [];
  div.innerHTML = items.map(item => `<p><button class="secondary" onclick="status('${item.task_id}')">status</button><b>${item.task_id}</b> ${item.status || ''} ${item.terminal ? '(terminal)' : ''}</p>`).join('') || '<p class="muted">No goals yet.</p>';
  show(r.body);
}
async function status(taskId) {
  const r = await api('/api/goals/' + encodeURIComponent(taskId));
  show(r.body);
}
async function submitGoal() {
  const token = document.getElementById('consoleToken').value;
  const payload = {
    project_key: document.getElementById('project').value,
    task_id: document.getElementById('taskId').value || undefined,
    objective: document.getElementById('objective').value,
    constraints: lines('constraints'),
    expected_checks: lines('checks'),
    commit_message: document.getElementById('commitMessage').value || undefined,
  };
  const r = await api('/api/goals', {method: 'POST', headers: {'Content-Type': 'application/json', 'X-ORIS-Console-Token': token}, body: JSON.stringify(payload)});
  show(r.body);
  await refreshGoals();
}
loadProjects().then(refreshGoals).catch(err => show(String(err)));
</script>
</body>
</html>
"""


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


if __name__ == "__main__":
    raise SystemExit(main())
