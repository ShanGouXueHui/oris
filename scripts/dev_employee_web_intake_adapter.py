#!/usr/bin/env python3
"""Thin OpenClaw/Web adapter client for ORIS Dev Employee intake service.

The adapter is intentionally small and local-only. It converts a Web/OpenClaw
payload into calls to the already-verified intake service.

Commands:
- projects: list registry project keys.
- submit: submit a goal payload JSON file.
- status: read a task status by task_id.

It does not execute shell commands, invoke Codex, mutate queues directly, or push
GitHub. Execution remains owned by intake service + enqueue API + supervised
bridge.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_ENV_FILE = Path.home() / ".config" / "oris" / "dev_employee_enqueue.env"
DEFAULT_BASE_URL = "http://127.0.0.1:18892"
AUTH_HEADER = "X-ORIS-Token"
TOKEN_KEY = "ORIS_DEV_EMPLOYEE_INTAKE_TOKEN"


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


def token(env_file: Path) -> str:
    value = os.environ.get(TOKEN_KEY) or load_env(env_file).get(TOKEN_KEY)
    if not value:
        raise SystemExit(f"ERROR: {TOKEN_KEY} missing from environment or {env_file}")
    return value


def require_loopback(base_url: str) -> str:
    if not base_url.startswith("http://127.0.0.1:") and not base_url.startswith("http://localhost:"):
        raise SystemExit("ERROR: refusing non-loopback intake URL")
    return base_url.rstrip("/")


def request(base_url: str, method: str, path: str, body: dict[str, Any] | None = None, auth_value: str | None = None) -> tuple[int, Any]:
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if auth_value:
        headers[AUTH_HEADER] = auth_value
    req = urllib.request.Request(base_url + path, method=method, data=data, headers=headers)
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
        return 599, {"error": "url_error", "message": str(exc)}


def normalize_submit_payload(raw: dict[str, Any]) -> dict[str, Any]:
    allowed = {"project_key", "task_id", "objective", "constraints", "expected_checks", "commit_message", "notes"}
    payload = {key: raw[key] for key in allowed if key in raw}
    if not payload.get("project_key"):
        raise SystemExit("ERROR: payload missing project_key")
    objective = str(payload.get("objective") or "").strip()
    if len(objective) < 20:
        raise SystemExit("ERROR: payload objective must be at least 20 characters")
    payload["objective"] = objective
    for list_key in ["constraints", "expected_checks", "notes"]:
        if list_key in payload and not isinstance(payload[list_key], list):
            raise SystemExit(f"ERROR: payload {list_key} must be a list")
    return payload


def print_result(status: int, body: Any) -> int:
    print(json.dumps({"http_status": status, "body": body}, ensure_ascii=False, indent=2))
    return 0 if 200 <= status < 300 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="OpenClaw/Web adapter client for ORIS Dev Employee intake service")
    parser.add_argument("--base-url", default=os.environ.get("ORIS_DEV_EMPLOYEE_INTAKE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--env-file", default=str(DEFAULT_ENV_FILE))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("projects")
    submit = sub.add_parser("submit")
    submit.add_argument("--payload", required=True, help="JSON file containing project_key/objective/constraints/checks")
    status = sub.add_parser("status")
    status.add_argument("--task-id", required=True)
    args = parser.parse_args()

    base_url = require_loopback(args.base_url)
    env_file = Path(args.env_file)
    if args.command == "projects":
        code, body = request(base_url, "GET", "/projects")
        return print_result(code, body)
    if args.command == "status":
        code, body = request(base_url, "GET", f"/goals/{args.task_id}")
        return print_result(code, body)
    if args.command == "submit":
        raw = json.loads(Path(args.payload).read_text(encoding="utf-8"))
        payload = normalize_submit_payload(raw)
        code, body = request(base_url, "POST", "/goals", body=payload, auth_value=token(env_file))
        return print_result(code, body)
    raise SystemExit("unreachable")


if __name__ == "__main__":
    raise SystemExit(main())
