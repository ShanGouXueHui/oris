#!/usr/bin/env python3
"""Validate Web Console audit logging for submit attempts.

This validator assumes the Web Console service has been restarted with the audit
patch. It sends a submit-disabled POST attempt and verifies that a local JSONL
audit event is written without token/header values.
"""

from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ORIS_DIR = Path("/home/admin/projects/oris")
ENV_FILE = Path.home() / ".config" / "oris" / "dev_employee_enqueue.env"
AUDIT_DIR = ORIS_DIR / "logs" / "dev_employee" / "web_console_audit"
REPORT_DIR = ORIS_DIR / "logs" / "dev_employee" / "web_console_audit_validation"
BASE_URL = "http://127.0.0.1:18893"
TOKEN_KEY = "ORIS_DEV_EMPLOYEE_WEB_CONSOLE_TOKEN"
TASK_ID = "web-console-audit-submit-disabled-20260529-r1"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def run(cmd: list[str], check: bool = False) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(cmd, cwd=str(ORIS_DIR), text=True, capture_output=True, check=False)
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, end="")
    if check and proc.returncode != 0:
        raise SystemExit(proc.returncode)
    return proc


def read_env() -> dict[str, str]:
    values: dict[str, str] = {}
    if ENV_FILE.exists():
        for raw in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def token() -> str:
    value = os.environ.get(TOKEN_KEY) or read_env().get(TOKEN_KEY)
    if not value:
        raise SystemExit(f"ERROR: {TOKEN_KEY} missing")
    return value


def request(method: str, path: str, token_value: str | None = None, body: dict[str, Any] | None = None) -> tuple[int, Any]:
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token_value:
        headers["X-ORIS-Console-Token"] = token_value
    req = urllib.request.Request(BASE_URL + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, {"raw": raw}


def audit_files() -> list[Path]:
    if not AUDIT_DIR.exists():
        return []
    return sorted(AUDIT_DIR.glob("web_console_audit_*.jsonl"))


def read_audit_events() -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for path in audit_files():
        for raw in path.read_text(encoding="utf-8").splitlines():
            if raw.strip():
                events.append(json.loads(raw))
    return events


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    tok = token()
    before_count = len(read_audit_events())
    payload = {
        "project_key": "oris-final-acceptance-api",
        "task_id": TASK_ID,
        "objective": "This submit attempt is expected to be blocked by submit_disabled while still writing an audit event.",
        "constraints": ["Do not create this task."],
        "expected_checks": [],
    }
    post_code, post_body = request("POST", "/api/goals", token_value=tok, body=payload)
    events = read_audit_events()
    matching = [
        event
        for event in events[before_count:]
        if event.get("action") == "submit_goal" and event.get("reason") == "submit_disabled"
    ]
    # Fall back to full scan in case another process wrote audit events concurrently.
    if not matching:
        matching = [
            event
            for event in events
            if event.get("action") == "submit_goal" and event.get("reason") == "submit_disabled"
        ]
    latest = matching[-1] if matching else {}
    serialized = json.dumps(latest, ensure_ascii=False, sort_keys=True).lower()
    forbidden_terms = ["token", "headers", "authorization", "x-oris-console-token", "x_oris_console_token", tok.lower()]
    forbidden_found = [term for term in forbidden_terms if term and term in serialized]
    report = {
        "validated_at": now_iso(),
        "ok": False,
        "post_code": post_code,
        "post_error": post_body.get("error") if isinstance(post_body, dict) else None,
        "audit_event_found": bool(latest),
        "audit_event_result": latest.get("result"),
        "audit_event_reason": latest.get("reason"),
        "audit_event_action": latest.get("action"),
        "audit_event_path": latest.get("path"),
        "audit_event_method": latest.get("method"),
        "audit_event_has_ts": bool(latest.get("ts")),
        "audit_event_keys": sorted(latest.keys()) if latest else [],
        "forbidden_terms_found": forbidden_found,
        "audit_files_count": len(audit_files()),
        "audit_events_before": before_count,
        "audit_events_after": len(events),
        "final_oris_tracked_status": run(["git", "status", "--short", "--untracked-files=no"]).stdout,
    }
    ok = (
        post_code == 403
        and report["post_error"] == "submit_disabled"
        and report["audit_event_found"] is True
        and report["audit_event_result"] == "rejected"
        and report["audit_event_reason"] == "submit_disabled"
        and report["audit_event_action"] == "submit_goal"
        and report["audit_event_path"] == "/api/goals"
        and report["audit_event_method"] == "POST"
        and report["audit_event_has_ts"] is True
        and not forbidden_found
    )
    report["ok"] = ok
    report_path = REPORT_DIR / "web-console-audit-20260529-r1.json"
    write_json(report_path, report)
    run(["git", "add", str(report_path.relative_to(ORIS_DIR))], check=True)
    staged = run(["git", "diff", "--cached", "--quiet"])
    if staged.returncode != 0:
        run(["git", "commit", "-m", "test(dev-employee): validate Web console audit logging"], check=True)
        run(["git", "push", "origin", "main"], check=True)
    run(["git", "log", "-1", "--oneline"], check=True)
    print(json.dumps({"ok": ok, "report_path": str(report_path)}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
