#!/usr/bin/env python3
"""Validate ORIS Dev Employee Web Console security gates.

Checks:
- Console service is reachable.
- Read API without console token returns 401.
- Read API with console token returns allowed projects and known evidence.
- POST /api/goals is disabled by default and returns 403 without creating tasks.
- No token values are printed.
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
REPORT_DIR = ORIS_DIR / "logs" / "dev_employee" / "web_console_security"
BASE_URL = "http://127.0.0.1:18893"
TASK_ID = "web-adapter-goal-livez-endpoint-20260529-r1"
TOKEN_KEY = "ORIS_DEV_EMPLOYEE_WEB_CONSOLE_TOKEN"


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


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    report: dict[str, Any] = {"validated_at": now_iso(), "task_id": TASK_ID}
    tok = token()
    health_code, health = request("GET", "/health")
    no_token_projects_code, no_token_projects = request("GET", "/api/projects")
    projects_code, projects = request("GET", "/api/projects", token_value=tok)
    status_code, status = request("GET", f"/api/goals/{TASK_ID}", token_value=tok)
    submit_payload = {
        "project_key": "oris-final-acceptance-api",
        "task_id": "web-console-security-submit-disabled-should-not-create",
        "objective": "This request must be rejected by the Web Console submit-disabled gate and must not enqueue a task.",
        "constraints": ["Do not create this task."],
        "expected_checks": [],
    }
    post_code, post_body = request("POST", "/api/goals", token_value=tok, body=submit_payload)
    task_check_code, task_check = request("GET", "/api/goals/web-console-security-submit-disabled-should-not-create", token_value=tok)
    report.update(
        {
            "ok": False,
            "health_code": health_code,
            "health_service": health.get("service") if isinstance(health, dict) else None,
            "no_token_projects_code": no_token_projects_code,
            "no_token_projects_error": no_token_projects.get("error") if isinstance(no_token_projects, dict) else None,
            "projects_code": projects_code,
            "projects": projects.get("projects") if isinstance(projects, dict) else None,
            "status_code": status_code,
            "task_status": status.get("status") if isinstance(status, dict) else None,
            "product_commit_sha": (status.get("github_evidence") or {}).get("product_commit_sha") if isinstance(status, dict) else None,
            "oris_evidence_commit_sha": (status.get("github_evidence") or {}).get("oris_evidence_commit_sha") if isinstance(status, dict) else None,
            "post_code": post_code,
            "post_error": post_body.get("error") if isinstance(post_body, dict) else None,
            "task_check_code": task_check_code,
            "task_check_status": task_check.get("status") if isinstance(task_check, dict) else None,
        }
    )
    ok = (
        health_code == 200
        and report["health_service"] == "dev_employee_web_console"
        and no_token_projects_code == 401
        and report["no_token_projects_error"] == "unauthorized"
        and projects_code == 200
        and report["projects"] == ["oris-final-acceptance-api"]
        and status_code == 200
        and report["task_status"] == "completed"
        and report["product_commit_sha"] == "f241f1626edec2f97e906680831ada29482b00ef"
        and report["oris_evidence_commit_sha"] == "9f50e41e30cffe419b515ae9613998a7cf33b4d0"
        and post_code == 403
        and report["post_error"] == "submit_disabled"
        and task_check_code == 200
        and report["task_check_status"] == "unknown"
    )
    report["ok"] = ok
    report["final_oris_tracked_status"] = run(["git", "status", "--short", "--untracked-files=no"]).stdout
    report_path = REPORT_DIR / "web-console-security-20260529-r1.json"
    write_json(report_path, report)
    run(["git", "add", str(report_path.relative_to(ORIS_DIR))], check=True)
    staged = run(["git", "diff", "--cached", "--quiet"])
    if staged.returncode != 0:
        run(["git", "commit", "-m", "test(dev-employee): validate Web console security gates"], check=True)
        run(["git", "push", "origin", "main"], check=True)
    run(["git", "log", "-1", "--oneline"], check=True)
    print(json.dumps({"ok": ok, "report_path": str(report_path)}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
