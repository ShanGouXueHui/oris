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
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 18893
DEFAULT_INTAKE_URL = "http://127.0.0.1:18892"
DEFAULT_ENV_FILE = Path.home() / ".config" / "oris" / "dev_employee_enqueue.env"
INTAKE_TOKEN_KEY = "ORIS_DEV_EMPLOYEE_INTAKE_TOKEN"
CONSOLE_TOKEN_KEY = "ORIS_DEV_EMPLOYEE_WEB_CONSOLE_TOKEN"
CONSOLE_AUTH_HEADER = "X-ORIS-Console-Token"
AUTH_HEADER = "X-ORIS-Token"


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def intake_base_url() -> str:
    url = os.environ.get("ORIS_DEV_EMPLOYEE_INTAKE_URL", DEFAULT_INTAKE_URL).rstrip("/")
    if not url.startswith("http://127.0.0.1:") and not url.startswith("http://localhost:"):
        raise RuntimeError("refusing non-loopback intake URL")
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
    raw = os.environ.get("ORIS_DEV_EMPLOYEE_WEB_CONSOLE_PROJECT_ALLOWLIST", "oris-final-acceptance-api")
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
    return {**body, "projects": [item for item in projects if item in allow]}


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
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if auth:
        headers[AUTH_HEADER] = intake_token()
    req = urllib.request.Request(intake_base_url() + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            text = resp.read().decode("utf-8")
            return resp.status, json.loads(text) if text else {}
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8")
        try:
            return exc.code, json.loads(text)
        except json.JSONDecodeError:
            return exc.code, {"raw": text}
    except urllib.error.URLError as exc:
        return 599, {"error": "intake_unreachable", "message": str(exc)}


def page() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>ORIS Dev Employee Console</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 0; background: #f6f7f9; color: #111827; }
    header { background: #111827; color: white; padding: 18px 24px; }
    main { max-width: 1180px; margin: 24px auto; padding: 0 18px; display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
    section { background: white; border: 1px solid #e5e7eb; border-radius: 14px; padding: 18px; box-shadow: 0 8px 24px rgba(15,23,42,.06); }
    label { display: block; font-weight: 650; margin: 12px 0 6px; }
    input, textarea, select { width: 100%; box-sizing: border-box; border: 1px solid #d1d5db; border-radius: 10px; padding: 10px; font: inherit; }
    textarea { min-height: 90px; }
    button { margin-top: 12px; border: 0; border-radius: 10px; padding: 10px 14px; background: #2563eb; color: white; font-weight: 700; cursor: pointer; }
    button.secondary { background: #374151; }
    pre { background: #0b1020; color: #d1e7ff; padding: 14px; border-radius: 12px; overflow: auto; max-height: 520px; }
    .muted { color: #6b7280; font-size: 13px; }
    .row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    .pill { display:inline-block; padding: 4px 9px; border-radius:999px; background:#e0f2fe; color:#075985; font-size:12px; font-weight:700; }
    @media (max-width: 900px) { main { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <header>
    <h1>ORIS Dev Employee Console</h1>
    <div class="muted">Local-only prototype over the verified intake/status service. Do not expose publicly without auth/reverse-proxy policy.</div>
  </header>
  <main>
    <section>
      <h2>Submit goal</h2>
      <div class="muted">Human supplies goal and constraints; ORIS decides routine engineering steps.</div>
      <label>Console API token</label>
      <input id="console_token" type="password" placeholder="paste local console token" />
      <div class="muted">Stored only in this browser localStorage. Do not expose publicly without reverse-proxy auth.</div>
      <label>Project</label>
      <select id="project_key"></select>
      <label>Task ID optional</label>
      <input id="task_id" placeholder="leave blank for generated id" />
      <label>Objective</label>
      <textarea id="objective" placeholder="Add a concrete product feature with acceptance criteria."></textarea>
      <label>Constraints one per line</label>
      <textarea id="constraints">Do not ask the human for routine engineering decisions.
Keep implementation minimal and deterministic.
Do not add external dependencies unless necessary.</textarea>
      <label>Expected checks one per line</label>
      <textarea id="expected_checks"></textarea>
      <label>Commit message optional</label>
      <input id="commit_message" placeholder="feat(...): ..." />
      <button onclick="submitGoal()">Submit goal</button>
      <button class="secondary" onclick="loadProjects()">Reload projects</button>
      <pre id="submit_result"></pre>
    </section>
    <section>
      <h2>Status & evidence</h2>
      <div class="row">
        <div>
          <label>Task ID</label>
          <input id="lookup_task_id" placeholder="task id" />
        </div>
        <div style="align-self:end">
          <button onclick="loadStatus()">Load status</button>
        </div>
      </div>
      <div id="summary"></div>
      <pre id="status_result"></pre>
    </section>
  </main>
<script>
const splitLines = (value) => value.split('\n').map(x => x.trim()).filter(Boolean);
function consoleToken() { return document.getElementById('console_token').value.trim(); }
function rememberToken() { localStorage.setItem('oris_console_token', consoleToken()); }
async function api(path, options={}) {
  const headers = Object.assign({}, options.headers || {});
  const token = consoleToken();
  if (token) headers['X-ORIS-Console-Token'] = token;
  const resp = await fetch(path, Object.assign({}, options, {headers}));
  const data = await resp.json();
  if (!resp.ok) throw new Error(JSON.stringify(data, null, 2));
  return data;
}
async function loadProjects() {
  rememberToken();
  const data = await api('/api/projects');
  const select = document.getElementById('project_key');
  select.innerHTML = '';
  for (const key of data.projects || []) {
    const opt = document.createElement('option'); opt.value = key; opt.textContent = key; select.appendChild(opt);
  }
}
async function submitGoal() {
  rememberToken();
  const payload = {
    project_key: document.getElementById('project_key').value,
    objective: document.getElementById('objective').value.trim(),
    constraints: splitLines(document.getElementById('constraints').value),
    expected_checks: splitLines(document.getElementById('expected_checks').value),
    notes: ['Submitted through ORIS local Web console prototype.']
  };
  const taskId = document.getElementById('task_id').value.trim();
  const commitMessage = document.getElementById('commit_message').value.trim();
  if (taskId) payload.task_id = taskId;
  if (commitMessage) payload.commit_message = commitMessage;
  const data = await api('/api/goals', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload) });
  document.getElementById('submit_result').textContent = JSON.stringify(data, null, 2);
  if (data.task_id) document.getElementById('lookup_task_id').value = data.task_id;
}
function renderSummary(data) {
  const ev = data.github_evidence || {};
  const files = (ev.files || []).map(f => `<li><code>${f.label}</code>: ${f.repo_path || f.local_path}</li>`).join('');
  document.getElementById('summary').innerHTML = `
    <p><span class="pill">${data.status || 'unknown'}</span></p>
    <p><b>Product:</b> <code>${ev.product_commit_sha || ''}</code></p>
    <p><b>Remote:</b> <code>${ev.product_remote_sha || ''}</code></p>
    <p><b>ORIS evidence:</b> <code>${ev.oris_evidence_commit_sha || ''}</code></p>
    <p><b>Evidence files</b></p><ul>${files}</ul>`;
}
async function loadStatus() {
  const taskId = document.getElementById('lookup_task_id').value.trim();
  if (!taskId) return;
  rememberToken();
  const data = await api('/api/goals/' + encodeURIComponent(taskId));
  renderSummary(data);
  document.getElementById('status_result').textContent = JSON.stringify(data, null, 2);
}
document.getElementById('console_token').value = localStorage.getItem('oris_console_token') || '';
loadProjects().catch(e => { document.getElementById('submit_result').textContent = String(e); });
</script>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    server_version = "oris-dev-employee-web-console/0.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"{self.address_string()} - {fmt % args}", flush=True)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path in {"/", "/index.html"}:
            return html_response(self, 200, page())
        if path == "/health":
            return json_response(self, 200, {"status": "ok", "service": "dev_employee_web_console"})
        if path == "/api/projects":
            if not console_auth_ok(self):
                return json_response(self, 401, {"error": "unauthorized"})
            status, body = intake_request("GET", "/projects")
            return json_response(self, status, filter_projects(body))
        if path == "/api/goals":
            if not console_auth_ok(self):
                return json_response(self, 401, {"error": "unauthorized"})
            status, body = intake_request("GET", "/goals")
            return json_response(self, status, body)
        if path.startswith("/api/goals/"):
            if not console_auth_ok(self):
                return json_response(self, 401, {"error": "unauthorized"})
            task_id = unquote(path.removeprefix("/api/goals/"))
            status, body = intake_request("GET", f"/goals/{task_id}")
            return json_response(self, status, body)
        return json_response(self, 404, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path != "/api/goals":
            return json_response(self, 404, {"error": "not_found"})
        try:
            if not console_auth_ok(self):
                return json_response(self, 401, {"error": "unauthorized"})
            if not submit_enabled():
                return json_response(self, 403, {"error": "submit_disabled"})
            length = int(self.headers.get("Content-Length") or "0")
            if length <= 0 or length > 80_000:
                return json_response(self, 400, {"error": "invalid_body_length"})
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            project_key = str(payload.get("project_key") or "")
            if project_key not in allowed_projects():
                return json_response(self, 403, {"error": "project_not_allowed", "project_key": project_key})
            status, body = intake_request("POST", "/goals", body=payload, auth=True)
            return json_response(self, status, body)
        except Exception as exc:
            return json_response(self, 400, {"error": type(exc).__name__, "message": str(exc)})


def main() -> int:
    host = os.environ.get("ORIS_DEV_EMPLOYEE_WEB_CONSOLE_HOST", DEFAULT_HOST)
    port = int(os.environ.get("ORIS_DEV_EMPLOYEE_WEB_CONSOLE_PORT", str(DEFAULT_PORT)))
    if host not in {"127.0.0.1", "localhost"}:
        raise SystemExit("Refusing to bind non-loopback host")
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"ORIS Dev Employee Web Console listening on http://{host}:{port}", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
