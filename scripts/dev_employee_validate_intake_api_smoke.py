#!/usr/bin/env python3
"""Validate local-only Dev Employee intake API without executing Codex.

The runner:
- ensures an intake token exists locally;
- stops the bridge so the smoke queued task cannot be consumed;
- starts dev_employee_intake_api.py on loopback;
- checks /health and /projects;
- POSTs a smoke /goals request;
- checks /goals/<task_id>;
- removes the smoke queue/catalog/prompt artifacts;
- restarts the bridge if it was active;
- commits a GitHub-verifiable smoke report.

It never commits secrets and never lets the smoke task execute.
"""

from __future__ import annotations

import json
import secrets
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ORIS_DIR = Path("/home/admin/projects/oris")
ENV_FILE = Path.home() / ".config" / "oris" / "dev_employee_enqueue.env"
REPORT_DIR = ORIS_DIR / "logs" / "dev_employee" / "intake_api_smoke"
LOG_DIR = ORIS_DIR / "logs" / "dev_employee"
QUEUE_DIR = ORIS_DIR / "orchestration" / "dev_employee_queue"
CATALOG_DIR = ORIS_DIR / "orchestration" / "dev_employee_intake_catalog"
PROMPT_DIR = ORIS_DIR / "run" / "dev_employee_prompts"
BRIDGE_SERVICE = "oris-dev-employee-bridge.service"
INTAKE_PORT = 18892
BASE_URL = f"http://127.0.0.1:{INTAKE_PORT}"
TASK_ID = "intake-smoke-noexec-20260529-r1"


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
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def ensure_intake_token() -> str:
    ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
    values = read_env()
    token = values.get("ORIS_DEV_EMPLOYEE_INTAKE_TOKEN")
    if token:
        return token
    token = secrets.token_urlsafe(32)
    with ENV_FILE.open("a", encoding="utf-8") as fh:
        fh.write(f"ORIS_DEV_EMPLOYEE_INTAKE_TOKEN={token}\n")
    ENV_FILE.chmod(0o600)
    return token


def service_active(service: str) -> bool:
    return run(["systemctl", "--user", "is-active", service]).stdout.strip() == "active"


def start_intake(log_path: Path) -> subprocess.Popen[str]:
    values = read_env()
    env = dict(**subprocess.os.environ)
    for key in ["ORIS_DEV_EMPLOYEE_INTAKE_TOKEN", "ORIS_DEV_EMPLOYEE_ENQUEUE_TOKEN"]:
        if values.get(key):
            env[key] = values[key]
    env["ORIS_DEV_EMPLOYEE_INTAKE_PORT"] = str(INTAKE_PORT)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_fh = log_path.open("w", encoding="utf-8")
    return subprocess.Popen(
        ["python3", "scripts/dev_employee_intake_api.py"],
        cwd=str(ORIS_DIR),
        text=True,
        stdout=log_fh,
        stderr=subprocess.STDOUT,
        env=env,
    )


def request(method: str, path: str, token: str | None = None, body: dict[str, Any] | None = None) -> tuple[int, Any]:
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["X-ORIS-Token"] = token
    req = urllib.request.Request(BASE_URL + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, {"raw": raw}


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def cleanup_smoke() -> list[str]:
    removed: list[str] = []
    for path in [
        QUEUE_DIR / f"{TASK_ID}.queued.json",
        QUEUE_DIR / f"{TASK_ID}.running.json",
        QUEUE_DIR / f"{TASK_ID}.done.json",
        QUEUE_DIR / f"{TASK_ID}.failed.json",
        CATALOG_DIR / f"{TASK_ID}.json",
        PROMPT_DIR / f"{TASK_ID}.md",
    ]:
        if path.exists():
            path.unlink()
            removed.append(str(path))
    return removed


def main() -> int:
    report: dict[str, Any] = {"task_id": TASK_ID, "started_at": now_iso()}
    intake_proc: subprocess.Popen[str] | None = None
    bridge_was_active = False
    token = ensure_intake_token()
    log_path = LOG_DIR / f"intake_api_smoke_{TASK_ID}.log"
    ok = False
    try:
        run(["git", "fetch", "origin", "main"], check=True)
        run(["git", "reset", "--hard", "origin/main"], check=True)
        run(["python3", "-m", "py_compile", "scripts/dev_employee_intake_api.py"], check=True)
        cleanup_smoke()
        bridge_was_active = service_active(BRIDGE_SERVICE)
        run(["systemctl", "--user", "stop", BRIDGE_SERVICE])
        time.sleep(2)
        intake_proc = start_intake(log_path)
        time.sleep(2)
        health_status, health = request("GET", "/health")
        projects_status, projects = request("GET", "/projects")
        goal_body = {
            "project_key": "oris-final-acceptance-api",
            "task_id": TASK_ID,
            "objective": "Smoke-test the ORIS Dev Employee intake API only. Do not execute product changes. This task is intentionally removed before the bridge is restarted.",
            "constraints": [
                "This is an intake API smoke test only.",
                "Do not ask the human for routine engineering decisions.",
            ],
            "expected_checks": [
                "/home/admin/projects/oris-final-acceptance-api/.venv/bin/python -m pytest -q",
            ],
            "commit_message": "test(dev-employee): intake api smoke",
            "notes": ["This queued descriptor will be deleted before bridge restart."],
        }
        post_status, post_body = request("POST", "/goals", token=token, body=goal_body)
        status_status, status_body = request("GET", f"/goals/{TASK_ID}")
        removed = cleanup_smoke()
        ok = (
            health_status == 200
            and health.get("status") == "ok"
            and projects_status == 200
            and "oris-final-acceptance-api" in projects.get("projects", [])
            and post_status == 201
            and post_body.get("task_id") == TASK_ID
            and post_body.get("status") == "queued"
            and status_status == 200
            and status_body.get("task_id") == TASK_ID
            and bool(removed)
        )
        report.update(
            {
                "ok": ok,
                "health_status": health_status,
                "health": health,
                "projects_status": projects_status,
                "projects_contains_final_acceptance": "oris-final-acceptance-api" in projects.get("projects", []),
                "post_status": post_status,
                "post_body": post_body,
                "task_status_status": status_status,
                "task_status_body": status_body,
                "removed_smoke_files": removed,
                "bridge_was_active": bridge_was_active,
                "log_path": str(log_path),
            }
        )
    finally:
        if intake_proc is not None:
            intake_proc.terminate()
            try:
                intake_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                intake_proc.kill()
        if bridge_was_active:
            run(["systemctl", "--user", "restart", BRIDGE_SERVICE])
            time.sleep(3)
            report["bridge_active_after"] = service_active(BRIDGE_SERVICE)
        report["finished_at"] = now_iso()
        report["final_oris_tracked_status"] = run(["git", "status", "--short", "--untracked-files=no"]).stdout
        report_path = REPORT_DIR / "intake-api-smoke-20260529-r1.json"
        write_json(report_path, report)
        run(["git", "add", str(report_path.relative_to(ORIS_DIR))], check=True)
        staged = run(["git", "diff", "--cached", "--quiet"])
        if staged.returncode != 0:
            run(["git", "commit", "-m", "test(dev-employee): validate intake API smoke"], check=True)
            run(["git", "push", "origin", "main"], check=True)
        run(["git", "log", "-1", "--oneline"], check=True)
        print(json.dumps({"ok": report.get("ok"), "report_path": str(report_path)}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
