#!/usr/bin/env python3
"""Validate Web/OpenClaw intake adapter without executing Codex.

The runner stops the supervised bridge, submits a smoke task through
`dev_employee_web_intake_adapter.py`, verifies adapter status output, removes
smoke artifacts, and restores the bridge.
"""

from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ORIS_DIR = Path("/home/admin/projects/oris")
QUEUE_DIR = ORIS_DIR / "orchestration" / "dev_employee_queue"
CATALOG_DIR = ORIS_DIR / "orchestration" / "dev_employee_intake_catalog"
PROMPT_DIR = ORIS_DIR / "run" / "dev_employee_prompts"
REPORT_DIR = ORIS_DIR / "logs" / "dev_employee" / "web_intake_adapter_smoke"
BRIDGE_SERVICE = "oris-dev-employee-bridge.service"
TASK_ID = "web-adapter-smoke-noexec-20260529-r1"
PAYLOAD_PATH = ORIS_DIR / "run" / "dev_employee_prompts" / f"{TASK_ID}.payload.json"


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


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_json_output(proc: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"raw_stdout": proc.stdout, "stderr": proc.stderr}


def service_active(service: str) -> bool:
    return run(["systemctl", "--user", "is-active", service]).stdout.strip() == "active"


def cleanup_smoke() -> list[str]:
    removed: list[str] = []
    for path in [
        QUEUE_DIR / f"{TASK_ID}.queued.json",
        QUEUE_DIR / f"{TASK_ID}.running.json",
        QUEUE_DIR / f"{TASK_ID}.done.json",
        QUEUE_DIR / f"{TASK_ID}.failed.json",
        CATALOG_DIR / f"{TASK_ID}.json",
        PROMPT_DIR / f"{TASK_ID}.md",
        PAYLOAD_PATH,
    ]:
        if path.exists():
            path.unlink()
            removed.append(str(path))
    return removed


def main() -> int:
    report: dict[str, Any] = {"task_id": TASK_ID, "started_at": now_iso()}
    bridge_was_active = False
    ok = False
    try:
        run(["git", "fetch", "origin", "main"], check=True)
        run(["git", "reset", "--hard", "origin/main"], check=True)
        run(["python3", "-m", "py_compile", "scripts/dev_employee_web_intake_adapter.py"], check=True)
        cleanup_smoke()
        projects_proc = run(["python3", "scripts/dev_employee_web_intake_adapter.py", "projects"])
        projects = parse_json_output(projects_proc)
        bridge_was_active = service_active(BRIDGE_SERVICE)
        run(["systemctl", "--user", "stop", BRIDGE_SERVICE])
        time.sleep(2)
        payload = {
            "project_key": "oris-final-acceptance-api",
            "task_id": TASK_ID,
            "objective": "Smoke-test the ORIS Web intake adapter only. Do not execute product changes. This task is intentionally removed before the bridge is restarted.",
            "constraints": [
                "This is a Web intake adapter smoke test only.",
                "Do not ask the human for routine engineering decisions."
            ],
            "expected_checks": [
                "/home/admin/projects/oris-final-acceptance-api/.venv/bin/python -m pytest -q"
            ],
            "commit_message": "test(dev-employee): Web adapter smoke",
            "notes": ["This queued descriptor will be deleted before bridge restart."]
        }
        write_json(PAYLOAD_PATH, payload)
        submit_proc = run(["python3", "scripts/dev_employee_web_intake_adapter.py", "submit", "--payload", str(PAYLOAD_PATH)])
        submit = parse_json_output(submit_proc)
        status_proc = run(["python3", "scripts/dev_employee_web_intake_adapter.py", "status", "--task-id", TASK_ID])
        status = parse_json_output(status_proc)
        removed = cleanup_smoke()
        projects_body = projects.get("body", {}) if isinstance(projects, dict) else {}
        submit_body = submit.get("body", {}) if isinstance(submit, dict) else {}
        status_body = status.get("body", {}) if isinstance(status, dict) else {}
        ok = (
            projects_proc.returncode == 0
            and "oris-final-acceptance-api" in projects_body.get("projects", [])
            and submit_proc.returncode == 0
            and submit.get("http_status") == 201
            and submit_body.get("task_id") == TASK_ID
            and submit_body.get("status") == "queued"
            and status_proc.returncode == 0
            and status.get("http_status") == 200
            and status_body.get("task_id") == TASK_ID
            and status_body.get("status") == "queued"
            and bool(removed)
        )
        report.update(
            {
                "ok": ok,
                "projects": projects,
                "submit": submit,
                "status": status,
                "removed_smoke_files": removed,
                "bridge_was_active": bridge_was_active,
            }
        )
    finally:
        cleanup_smoke()
        if bridge_was_active:
            run(["systemctl", "--user", "restart", BRIDGE_SERVICE])
            time.sleep(3)
            report["bridge_active_after"] = service_active(BRIDGE_SERVICE)
        report["finished_at"] = now_iso()
        report["final_oris_tracked_status"] = run(["git", "status", "--short", "--untracked-files=no"]).stdout
        report_path = REPORT_DIR / "web-intake-adapter-smoke-20260529-r1.json"
        write_json(report_path, report)
        run(["git", "add", str(report_path.relative_to(ORIS_DIR))], check=True)
        staged = run(["git", "diff", "--cached", "--quiet"])
        if staged.returncode != 0:
            run(["git", "commit", "-m", "test(dev-employee): validate Web intake adapter smoke"], check=True)
            run(["git", "push", "origin", "main"], check=True)
        run(["git", "log", "-1", "--oneline"], check=True)
        print(json.dumps({"ok": report.get("ok"), "report_path": str(report_path)}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
