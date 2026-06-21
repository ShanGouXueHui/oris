from __future__ import annotations

import json
import os
import urllib.error as urlerror
import urllib.request as urlrequest
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any

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
