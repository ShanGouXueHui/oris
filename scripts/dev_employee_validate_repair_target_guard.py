#!/usr/bin/env python3
"""Validate repair-from-triage product path/repo guard.

This runner verifies two behaviors using an existing controlled fixture failure:
1. Plan generation is allowed, but the generated plan records target_guard.enqueue_allowed=false.
2. Enqueue is rejected when product_path basename does not match product_repo slug, and no queue task is created.

It writes a validation report under logs/dev_employee/repair_guard_tests/ and commits it.
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ORIS_DIR = Path("/home/admin/projects/oris")
FAILED_TASK_ID = "failure-evidence-auto-triage-host-checks-20260526-r1"
PLAN_TASK_ID = "guard-validate-plan-mismatch-20260526-r1"
ENQUEUE_TASK_ID = "guard-validate-enqueue-rejected-20260526-r1"
REPORT_DIR = ORIS_DIR / "logs" / "dev_employee" / "repair_guard_tests"
QUEUE_DIR = ORIS_DIR / "orchestration" / "dev_employee_queue"
REPAIR_PLAN_DIR = ORIS_DIR / "logs" / "dev_employee" / "repair_plans"


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


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def queue_files(task_id: str) -> list[str]:
    patterns = [
        f"{task_id}.queued.json",
        f"{task_id}.running.json",
        f"{task_id}.done.json",
        f"{task_id}.failed.json",
    ]
    return [str(QUEUE_DIR / pattern) for pattern in patterns if (QUEUE_DIR / pattern).exists()]


def main() -> int:
    run(["git", "fetch", "origin", "main"], check=True)
    run(["git", "reset", "--hard", "origin/main"], check=True)
    run(["python3", "-m", "py_compile", "scripts/dev_employee_repair_from_triage.py"], check=True)

    plan_proc = run([
        "python3",
        "scripts/dev_employee_repair_from_triage.py",
        "--failed-task-id",
        FAILED_TASK_ID,
        "--new-task-id",
        PLAN_TASK_ID,
    ])
    plan_path = REPAIR_PLAN_DIR / f"{PLAN_TASK_ID}.json"
    plan = read_json(plan_path) if plan_path.exists() else {}
    target_guard = plan.get("target_guard", {}) if isinstance(plan, dict) else {}

    enqueue_proc = run([
        "python3",
        "scripts/dev_employee_repair_from_triage.py",
        "--failed-task-id",
        FAILED_TASK_ID,
        "--new-task-id",
        ENQUEUE_TASK_ID,
        "--enqueue",
    ])
    created_queue_files = queue_files(ENQUEUE_TASK_ID)

    report = {
        "validated_at": now_iso(),
        "failed_task_id": FAILED_TASK_ID,
        "plan_task_id": PLAN_TASK_ID,
        "enqueue_task_id": ENQUEUE_TASK_ID,
        "plan_generation": {
            "return_code": plan_proc.returncode,
            "plan_path": str(plan_path),
            "target_guard": target_guard,
        },
        "enqueue_attempt": {
            "return_code": enqueue_proc.returncode,
            "stdout_tail": enqueue_proc.stdout[-2000:],
            "stderr_tail": enqueue_proc.stderr[-2000:],
            "created_queue_files": created_queue_files,
        },
        "expected": {
            "plan_return_code": 0,
            "target_guard_enqueue_allowed": False,
            "enqueue_return_code_nonzero": True,
            "created_queue_files": [],
        },
    }
    ok = (
        plan_proc.returncode == 0
        and target_guard.get("enqueue_allowed") is False
        and bool(target_guard.get("mismatch_reason"))
        and enqueue_proc.returncode != 0
        and not created_queue_files
    )
    report["ok"] = ok

    report_path = REPORT_DIR / "repair-target-guard-20260526-r1.json"
    write_json(report_path, report)
    run(["git", "add", str(report_path.relative_to(ORIS_DIR))], check=True)
    staged = run(["git", "diff", "--cached", "--quiet"])
    if staged.returncode != 0:
        run(["git", "commit", "-m", "test(dev-employee): validate repair target guard"], check=True)
        run(["git", "push", "origin", "main"], check=True)
    run(["git", "log", "-1", "--oneline"], check=True)
    print(json.dumps({"ok": ok, "report_path": str(report_path)}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
