#!/usr/bin/env python3
"""Conversation-first ORIS Dev Employee Web Console v3.

Default route `/` is a chat experience. The engineering form/JSON console is
preserved at `/admin`. Chat requests are translated through the conversation
orchestrator into the existing intake v2 control plane.
"""

from __future__ import annotations

import json
import os
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import unquote, urlparse

import dev_employee_web_console as web_base
import dev_employee_web_console_v2 as admin_console
from dev_employee_chat_orchestrator import process_message, refresh_session
from dev_employee_chat_store import DEFAULT_CHAT_STORE

DEFAULT_HOST = web_base.DEFAULT_HOST
DEFAULT_PORT = web_base.DEFAULT_PORT
COOKIE_NAME = "oris_chat_session"


def chat_page() -> str:
    return r'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>ORIS AI 开发员工</title>
  <style>
    :root { color-scheme: light; --bg:#f4f7fb; --panel:#fff; --line:#dbe3ef; --text:#172033; --muted:#64748b; --brand:#2563eb; --brand2:#1d4ed8; --user:#e8f1ff; --assistant:#fff; --danger:#b42318; }
    * { box-sizing:border-box; }
    body { margin:0; font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif; background:var(--bg); color:var(--text); }
    .shell { min-height:100vh; display:grid; grid-template-rows:auto 1fr; }
    header { background:rgba(255,255,255,.94); border-bottom:1px solid var(--line); padding:14px 24px; display:flex; justify-content:space-between; align-items:center; position:sticky; top:0; z-index:10; backdrop-filter:blur(12px); }
    .brand { display:flex; gap:12px; align-items:center; }
    .logo { width:38px; height:38px; border-radius:12px; display:grid; place-items:center; background:linear-gradient(135deg,var(--brand),#7c3aed); color:#fff; font-weight:800; }
    h1 { font-size:17px; margin:0; }
    .sub { font-size:12px; color:var(--muted); margin-top:2px; }
    header a { color:var(--muted); font-size:13px; text-decoration:none; }
    main { width:min(980px,100%); margin:0 auto; min-height:0; display:grid; grid-template-rows:1fr auto; padding:18px 18px 24px; gap:14px; }
    #conversation { min-height:58vh; overflow:auto; padding:4px 2px 24px; }
    .message { display:flex; margin:14px 0; }
    .message.user { justify-content:flex-end; }
    .bubble { max-width:min(760px,88%); border:1px solid var(--line); border-radius:18px; padding:12px 15px; background:var(--assistant); box-shadow:0 3px 15px rgba(15,23,42,.04); white-space:pre-wrap; line-height:1.55; }
    .user .bubble { background:var(--user); border-color:#cfe0ff; }
    .meta { font-size:11px; color:var(--muted); margin-top:7px; }
    .task-card { max-width:min(760px,92%); margin:8px 0 16px 0; background:var(--panel); border:1px solid var(--line); border-radius:18px; padding:16px; box-shadow:0 8px 24px rgba(15,23,42,.06); }
    .task-top { display:flex; justify-content:space-between; gap:12px; align-items:flex-start; }
    .task-title { font-weight:700; }
    .status { font-size:12px; border-radius:999px; padding:5px 9px; background:#eef4ff; color:#1d4ed8; white-space:nowrap; }
    .actions { display:flex; flex-wrap:wrap; gap:8px; margin-top:14px; }
    button { border:0; border-radius:12px; padding:10px 14px; font-weight:650; cursor:pointer; background:var(--brand); color:#fff; }
    button:hover { background:var(--brand2); }
    button.secondary { color:var(--text); background:#edf2f7; }
    button.danger { background:#fff1f0; color:var(--danger); border:1px solid #ffd3cf; }
    details { margin-top:12px; color:var(--muted); font-size:12px; }
    details pre { overflow:auto; background:#0f172a; color:#dce7f7; padding:12px; border-radius:12px; font-size:11px; }
    .composer { background:var(--panel); border:1px solid var(--line); border-radius:20px; padding:12px; box-shadow:0 12px 34px rgba(15,23,42,.09); }
    textarea { width:100%; border:0; resize:none; min-height:70px; max-height:200px; padding:8px; font:inherit; color:var(--text); outline:none; }
    .composer-row { display:flex; align-items:center; justify-content:space-between; gap:12px; }
    #project { color:var(--muted); font-size:12px; }
    .hint { color:var(--muted); font-size:12px; }
    #error { color:var(--danger); font-size:13px; min-height:18px; margin:6px 4px 0; }
    .typing { color:var(--muted); font-size:13px; margin:10px 4px; }
    @media (max-width:640px) { header { padding:12px 14px; } main { padding:10px; } .bubble { max-width:94%; } .sub { display:none; } }
  </style>
</head>
<body>
<div class="shell">
  <header>
    <div class="brand"><div class="logo">O</div><div><h1>ORIS AI 开发员工</h1><div class="sub">OpenClaw 对话编排 · ORIS 任务治理 · Codex 代码执行</div></div></div>
    <a href="/admin">工程管理台</a>
  </header>
  <main>
    <section id="conversation" aria-live="polite"></section>
    <section>
      <div class="composer">
        <textarea id="input" placeholder="例如：给 oris-final-acceptance-api 增加一个 /healthz 接口，自己完成并测试。"></textarea>
        <div class="composer-row"><div><div id="project">尚未选择项目</div><div class="hint">Enter 发送，Shift+Enter 换行</div></div><button id="send">发送</button></div>
      </div>
      <div id="error"></div>
    </section>
  </main>
</div>
<script>
let sessionId = null;
let csrfToken = null;
let lastSignature = '';
const conversation = document.getElementById('conversation');
const input = document.getElementById('input');
const errorBox = document.getElementById('error');
const projectBox = document.getElementById('project');
const sendButton = document.getElementById('send');

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[ch]));
}
function signature(session) { return JSON.stringify([session.updated_at, (session.messages || []).length, session.current_task_id]); }
function render(session) {
  const sig = signature(session);
  if (sig === lastSignature) return;
  lastSignature = sig;
  projectBox.textContent = session.selected_project ? `当前项目：${session.selected_project}` : '尚未选择项目';
  conversation.innerHTML = '';
  for (const message of (session.messages || [])) {
    if (message.type === 'task_card') { renderTaskCard(message.metadata || {}); continue; }
    const row = document.createElement('div');
    row.className = 'message ' + (message.role === 'user' ? 'user' : 'assistant');
    row.innerHTML = `<div class="bubble">${escapeHtml(message.content)}<div class="meta">${escapeHtml(message.created_at || '')}</div></div>`;
    conversation.appendChild(row);
  }
  conversation.scrollTop = conversation.scrollHeight;
}
function renderTaskCard(card) {
  const block = document.createElement('div');
  block.className = 'task-card';
  const actions = (card.actions || []).map(action => {
    if (action === 'cancel') return '<button class="danger" onclick="quickAction(\'停止任务\')">停止任务</button>';
    if (action === 'retry') return '<button onclick="quickAction(\'重试\')">重试</button>';
    if (action === 'refresh') return '<button class="secondary" onclick="refresh(true)">刷新进度</button>';
    return '';
  }).join('');
  block.innerHTML = `<div class="task-top"><div><div class="task-title">${escapeHtml(card.project_name || '当前任务')}</div><div class="meta">${escapeHtml(card.task_id || '')}</div></div><div class="status">${escapeHtml(card.plain_status || '处理中')}</div></div><div class="actions">${actions}</div><details><summary>技术详情</summary><pre>${escapeHtml(JSON.stringify(card.technical || {}, null, 2))}</pre></details>`;
  conversation.appendChild(block);
}
async function request(path, options = {}) {
  const headers = Object.assign({'Accept':'application/json'}, options.headers || {});
  if (csrfToken && options.method && options.method !== 'GET') headers['X-ORIS-Chat-CSRF'] = csrfToken;
  const response = await fetch(path, Object.assign({}, options, {headers, credentials:'same-origin'}));
  let data = {};
  try { data = await response.json(); } catch (_) {}
  if (!response.ok) throw new Error(data.message || data.error || `HTTP ${response.status}`);
  return data;
}
async function bootstrap() {
  try {
    const data = await request('/api/chat/bootstrap');
    sessionId = data.session_id;
    csrfToken = data.csrf_token;
    render(data.session);
  } catch (error) { errorBox.textContent = String(error); }
}
async function send(textOverride = null) {
  const text = (textOverride ?? input.value).trim();
  if (!text || !sessionId) return;
  errorBox.textContent = '';
  sendButton.disabled = true;
  if (textOverride === null) input.value = '';
  try {
    const data = await request('/api/chat/messages', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({session_id:sessionId, message:text})});
    render(data.session);
  } catch (error) { errorBox.textContent = String(error); }
  finally { sendButton.disabled = false; input.focus(); }
}
async function refresh(append = false) {
  if (!sessionId) return;
  try {
    const data = await request(`/api/chat/session?session_id=${encodeURIComponent(sessionId)}&append=${append ? '1' : '0'}`);
    render(data.session);
  } catch (error) { errorBox.textContent = String(error); }
}
function quickAction(text) { send(text); }
sendButton.addEventListener('click', () => send());
input.addEventListener('keydown', event => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); send(); } });
bootstrap().then(() => { input.focus(); setInterval(() => refresh(false), 5000); });
</script>
</body>
</html>'''


def html_response(handler: BaseHTTPRequestHandler, status: int, body: str) -> None:
    encoded = body.encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Content-Length", str(len(encoded)))
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("X-Content-Type-Options", "nosniff")
    handler.send_header("Referrer-Policy", "same-origin")
    handler.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
    handler.end_headers()
    handler.wfile.write(encoded)


def json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict[str, Any], *, set_cookie: str | None = None) -> None:
    encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(encoded)))
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("X-Content-Type-Options", "nosniff")
    if set_cookie:
        handler.send_header("Set-Cookie", set_cookie)
    handler.end_headers()
    handler.wfile.write(encoded)


def read_body(handler: BaseHTTPRequestHandler, max_length: int = 40_000) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length") or "0")
    if length < 0 or length > max_length:
        raise ValueError("invalid_body_length")
    if length == 0:
        return {}
    payload = json.loads(handler.rfile.read(length).decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("body must be a JSON object")
    return payload


def cookie_session_id(handler: BaseHTTPRequestHandler) -> str | None:
    raw = handler.headers.get("Cookie") or ""
    jar = cookies.SimpleCookie()
    try:
        jar.load(raw)
    except cookies.CookieError:
        return None
    morsel = jar.get(COOKIE_NAME)
    return morsel.value if morsel else None


def session_cookie(session_id: str) -> str:
    jar = cookies.SimpleCookie()
    jar[COOKIE_NAME] = session_id
    jar[COOKIE_NAME]["path"] = "/"
    jar[COOKIE_NAME]["httponly"] = True
    jar[COOKIE_NAME]["secure"] = True
    jar[COOKIE_NAME]["samesite"] = "Strict"
    jar[COOKIE_NAME]["max-age"] = 60 * 60 * 24 * 30
    return jar.output(header="").strip()


def csrf_ok(handler: BaseHTTPRequestHandler, session: dict[str, Any]) -> bool:
    supplied = handler.headers.get("X-ORIS-Chat-CSRF") or ""
    expected = str(session.get("csrf_token") or "")
    import hmac

    return bool(supplied and expected and hmac.compare_digest(supplied, expected))


def admin_get(handler: BaseHTTPRequestHandler, path: str) -> bool:
    if path == "/admin":
        html_response(handler, 200, admin_console.page())
        return True
    if path == "/api/projects":
        if not web_base.console_auth_ok(handler):
            json_response(handler, 401, {"error": "unauthorized"})
            return True
        status, body = web_base.intake_request("GET", "/projects")
        json_response(handler, status, web_base.filter_projects(body))
        return True
    if path == "/api/goals":
        if not web_base.console_auth_ok(handler):
            json_response(handler, 401, {"error": "unauthorized"})
            return True
        status, body = web_base.intake_request("GET", "/goals")
        json_response(handler, status, body)
        return True
    if path.startswith("/api/goals/"):
        if not web_base.console_auth_ok(handler):
            json_response(handler, 401, {"error": "unauthorized"})
            return True
        task_id = unquote(path.removeprefix("/api/goals/"))
        status, body = web_base.intake_request("GET", f"/goals/{task_id}")
        json_response(handler, status, body)
        return True
    return False


class Handler(BaseHTTPRequestHandler):
    server_version = "oris-dev-employee-web-console/0.3"

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"{self.address_string()} - {fmt % args}", flush=True)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        if path in {"/", "/index.html"}:
            return html_response(self, 200, chat_page())
        if path == "/health":
            return json_response(
                self,
                200,
                {
                    "status": "ok",
                    "service": "dev_employee_web_console_v3",
                    "default_experience": "conversation",
                    "admin_route": "/admin",
                    "openclaw_provider_configured": bool(os.environ.get("ORIS_OPENCLAW_CHAT_URL", "").strip()),
                },
            )
        if path == "/api/chat/bootstrap":
            existing_id = cookie_session_id(self)
            session = None
            if existing_id:
                try:
                    session = DEFAULT_CHAT_STORE.read(existing_id)
                except (FileNotFoundError, ValueError, json.JSONDecodeError):
                    session = None
            if session is None:
                actor = self.headers.get("X-Forwarded-User") or "web-user"
                session = DEFAULT_CHAT_STORE.create(actor=actor)
            return json_response(
                self,
                200,
                {
                    "session_id": session["session_id"],
                    "csrf_token": session["csrf_token"],
                    "session": DEFAULT_CHAT_STORE.public_view(session),
                },
                set_cookie=session_cookie(session["session_id"]),
            )
        if path == "/api/chat/session":
            from urllib.parse import parse_qs

            query = parse_qs(parsed.query)
            session_id = str((query.get("session_id") or [cookie_session_id(self) or ""])[0])
            if not session_id:
                return json_response(self, 400, {"error": "session_id_required"})
            append = str((query.get("append") or ["0"])[0]) == "1"
            try:
                session = refresh_session(session_id, append_if_changed=append)
                return json_response(self, 200, {"session": session})
            except FileNotFoundError:
                return json_response(self, 404, {"error": "session_not_found"})
        if admin_get(self, path):
            return
        return json_response(self, 404, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        try:
            if path == "/api/chat/messages":
                body = read_body(self)
                session_id = str(body.get("session_id") or cookie_session_id(self) or "")
                if not session_id:
                    return json_response(self, 400, {"error": "session_id_required"})
                session = DEFAULT_CHAT_STORE.read(session_id)
                if not csrf_ok(self, session):
                    return json_response(self, 403, {"error": "csrf_invalid"})
                message = str(body.get("message") or "")
                updated = process_message(session_id, message)
                web_base.write_audit_event(
                    self,
                    {
                        "action": "chat_message",
                        "result": "processed",
                        "session_id": session_id,
                        "message_length": len(message),
                        "current_task_id": updated.get("current_task_id"),
                        "provider": updated.get("provider"),
                    },
                )
                return json_response(self, 200, {"session": updated})

            if path == "/api/goals" or (path.startswith("/api/goals/") and path.rsplit("/", 1)[-1] in {"cancel", "retry"}):
                if not web_base.console_auth_ok(self):
                    return json_response(self, 401, {"error": "unauthorized"})
                if not web_base.submit_enabled():
                    return json_response(self, 403, {"error": "submit_disabled"})
                body = read_body(self, max_length=80_000)
                if path == "/api/goals":
                    project_key = str(body.get("project_key") or "")
                    if project_key not in web_base.allowed_projects():
                        return json_response(self, 403, {"error": "project_not_allowed"})
                    status, payload = web_base.intake_request("POST", "/goals", body=body, auth=True)
                    return json_response(self, status, payload)
                action = path.rsplit("/", 1)[-1]
                task_id = unquote(path.removeprefix("/api/goals/").removesuffix(f"/{action}")).strip("/")
                body.setdefault("requested_by", "admin-console")
                status, payload = web_base.intake_request("POST", f"/goals/{task_id}/{action}", body=body, auth=True)
                return json_response(self, status, payload)
            return json_response(self, 404, {"error": "not_found"})
        except FileNotFoundError:
            return json_response(self, 404, {"error": "session_not_found"})
        except ValueError as exc:
            return json_response(self, 400, {"error": "invalid_request", "message": str(exc)})
        except Exception as exc:
            web_base.write_audit_event(
                self,
                {
                    "action": "chat_or_admin_request",
                    "result": "error",
                    "reason": type(exc).__name__,
                },
            )
            return json_response(self, 500, {"error": "internal_error", "message": type(exc).__name__})


def main() -> int:
    host = os.environ.get("ORIS_DEV_EMPLOYEE_WEB_CONSOLE_HOST", DEFAULT_HOST)
    port = int(os.environ.get("ORIS_DEV_EMPLOYEE_WEB_CONSOLE_PORT", str(DEFAULT_PORT)))
    if host not in {"127.0.0.1", "localhost"}:
        raise SystemExit("Refusing to bind non-loopback host")
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"ORIS conversational Web Console v3 listening on http://{host}:{port}", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
