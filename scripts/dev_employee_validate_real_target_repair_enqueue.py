#!/usr/bin/env python3
"""Validate positive repair enqueue behavior for a real product target pair.

Safety design:
- Stops the supervised bridge before enqueue so Codex cannot pick up this
  synthetic repair task.
- Generates planning-only synthetic failure evidence and triage for the real
  product target pair.
- Runs repair_from_triage.py with --enqueue and verifies a queued descriptor is
  created through the loopback enqueue API.
- Captures and removes the queued descriptor before restarting the bridge.
- Commits only diagnostic evidence/report files, not runtime queue JSON.

No product repository files are modified.
"""

from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ORIS_DIR = Path("/home/admin/projects/oris")
RUN_DIR = ORIS_DIR / "orchestration" / "task_runs"
TRIAGE_DIR = ORIS_DIR / "logs" / "dev_employee" / "failure_triage"
REPAIR_PLAN_DIR = ORIS_DIR / "logs" / "dev_employee" / "repair_plans"
REPORT_DIR = ORIS_DIR / "logs" / "dev_employee" / "repair_enqueue_tests"
QUEUE_DIR = ORIS_DIR / "orchestration" / "dev_employee_queue"
FAILED_TASK_ID = "failure-evidence-real-target-enqueue-only-20260526-r1"
REPAIR_TASK_ID = "repair-real-target-enqueue-only-20260526-r1"
PRODUCT_PATH = "/home/admin/projects/oris-final-acceptance-api"
PRODUCT_REPO = "ShanGouXueHui/oris-final-acceptance-api"
BRIDGE_SERVICE = "oris-dev-employee-bridge.service"
ENQUEUE_SERVICE = "oris-dev-employee-enqueue.service"


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


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def service_is_active(service: str) -> bool:
    return run(["systemctl", "--user", "is-active", service]).stdout.strip() == "active"


def stop_bridge() -> bool:
    was_active = service_is_active(BRIDGE_SERVICE)
    run(["systemctl", "--user", "stop", BRIDGE_SERVICE])
    time.sleep(2)
    active_after = service_is_active(BRIDGE_SERVICE)
    if active_after:
        raise SystemExit(f"ERROR: {BRIDGE_SERVICE} still active after stop")
    return was_active


def restart_bridge_if_needed(was_active: bool) -> None:
    if was_active:
        run(["systemctl", "--user", "restart", BRIDGE_SERVICE])
        time.sleep(3)
        run(["systemctl", "--user", "is-active", BRIDGE_SERVICE], check=True)


def write_synthetic_failure_and_triage() -> tuple[Path, Path]:
    failure_path = RUN_DIR / f"{FAILED_TASK_ID}.failure_result.json"
    triage_path = TRIAGE_DIR / f"{FAILED_TASK_ID}.json"
    failure = {
        "task_id": FAILED_TASK_ID,
        "status": "blocked_host_checks_failed",
        "updated_at": now_iso(),
        "strict_result_schema": True,
        "task_objective": "Synthetic real-target repair enqueue validation. Do not let bridge process this task.",
        "failure_stage": "blocked_host_checks_failed",
        "product_path": PRODUCT_PATH,
        "codex_result_path": str(RUN_DIR / f"{FAILED_TASK_ID}.codex_result.json"),
        "codex_log_path": str(ORIS_DIR / "logs" / "dev_employee" / f"{FAILED_TASK_ID}.codex.log"),
        "next_recommended_action": "Validate repair enqueue descriptor creation only; do not modify product code.",
        "checks": {
            "ok": False,
            "python_bin": f"{PRODUCT_PATH}/.venv/bin/python",
            "results": [
                {
                    "cmd": f"{PRODUCT_PATH}/.venv/bin/python -m pytest -q",
                    "return_code": 1,
                    "log": str(ORIS_DIR / "logs" / "dev_employee" / f"{FAILED_TASK_ID}_host_pytest.txt"),
                }
            ],
        },
    }
    triage = {
        "task_id": FAILED_TASK_ID,
        "triaged_at": now_iso(),
        "source_evidence": str(failure_path),
        "status": "blocked_host_checks_failed",
        "strict_result_schema": True,
        "classification": {
            "category": "host_checks_failed",
            "root_cause": "Synthetic positive repair-enqueue validation failure; no real product failure is asserted.",
            "routine_autonomous_repair_allowed": True,
            "recommended_action": "Validate enqueue descriptor creation only while bridge is stopped.",
            "repair_scope": "product_or_test_environment",
            "failed_checks": [
                {
                    "cmd": f"{PRODUCT_PATH}/.venv/bin/python -m pytest -q",
                    "return_code": 1,
                    "log": str(ORIS_DIR / "logs" / "dev_employee" / f"{FAILED_TASK_ID}_host_pytest.txt"),
                }
            ],
        },
        "evidence_links": {
            "codex_log_path": failure["codex_log_path"],
            "codex_result_path": failure["codex_result_path"],
        },
        "next_step_contract": {
            "ask_human_for_routine_decision": False,
            "rerun_requires_new_task_id": True,
            "must_preserve_original_failure_evidence": True,
        },
    }
    write_json(failure_path, failure)
    write_json(triage_path, triage)
    return failure_path, triage_path


def queue_paths(task_id: str) -> list[Path]:
    return [
        QUEUE_DIR / f"{task_id}.queued.json",
        QUEUE_DIR / f"{task_id}.running.json",
        QUEUE_DIR / f"{task_id}.done.json",
        QUEUE_DIR / f"{task_id}.failed.json",
    ]


def cleanup_queue(task_id: str) -> list[str]:
    removed = []
    for path in queue_paths(task_id):
        if path.exists():
            removed.append(str(path))
            path.unlink()
    return removed


def product_status() -> str:
    proc = subprocess.run(["git", "status", "--short"], cwd=PRODUCT_PATH, text=True, capture_output=True, check=False)
    return proc.stdout


def main() -> int:
    bridge_was_active = False
    report: dict[str, Any] = {
        "validated_at": now_iso(),
        "failed_task_id": FAILED_TASK_ID,
        "repair_task_id": REPAIR_TASK_ID,
        "product_path": PRODUCT_PATH,
        "product_repo": PRODUCT_REPO,
    }
    try:
        run(["git", "fetch", "origin", "main"], check=True)
        run(["git", "reset", "--hard", "origin/main"], check=True)
        run(["python3", "-m", "py_compile", "scripts/dev_employee_repair_from_triage.py"], check=True)
        run(["systemctl", "--user", "is-active", ENQUEUE_SERVICE], check=True)
        product_status_before = product_status()
        bridge_was_active = stop_bridge()
        failure_path, triage_path = write_synthetic_failure_and_triage()
        enqueue_proc = run([
            "python3",
            "scripts/dev_employee_repair_from_triage.py",
            "--failed-task-id",
            FAILED_TASK_ID,
            "--new-task-id",
            REPAIR_TASK_ID,
            "--product-path",
            PRODUCT_PATH,
            "--product-repo",
            PRODUCT_REPO,
            "--enqueue",
            "--commit-plan",
        ])
        plan_path = REPAIR_PLAN_DIR / f"{REPAIR_TASK_ID}.json"
        plan = read_json(plan_path) if plan_path.exists() else {}
        queued_path = QUEUE_DIR / f"{REPAIR_TASK_ID}.queued.json"
        queued_descriptor = read_json(queued_path) if queued_path.exists() else None
        removed_queue_files = cleanup_queue(REPAIR_TASK_ID)
        product_status_after = product_status()
        target_guard = plan.get("target_guard", {}) if isinstance(plan, dict) else {}
        descriptor_ok = isinstance(queued_descriptor, dict) and queued_descriptor.get("task_id") == REPAIR_TASK_ID
        ok = (
            enqueue_proc.returncode == 0
            and target_guard.get("enqueue_allowed") is True
            and target_guard.get("mismatch_reason") is None
            and descriptor_ok
            and bool(removed_queue_files)
            and product_status_before == product_status_after
        )
        report.update(
            {
                "ok": ok,
                "bridge_was_active": bridge_was_active,
                "failure_path": str(failure_path),
                "triage_path": str(triage_path),
                "plan_path": str(plan_path),
                "enqueue_return_code": enqueue_proc.returncode,
                "enqueue_stdout_tail": enqueue_proc.stdout[-2000:],
                "enqueue_stderr_tail": enqueue_proc.stderr[-2000:],
                "target_guard": target_guard,
                "queued_descriptor_snapshot": queued_descriptor,
                "removed_queue_files": removed_queue_files,
                "product_status_before": product_status_before,
                "product_status_after": product_status_after,
                "expected": {
                    "enqueue_return_code": 0,
                    "target_guard_enqueue_allowed": True,
                    "queued_descriptor_created": True,
                    "queue_descriptor_removed_before_bridge_restart": True,
                    "product_status_unchanged": True,
                },
            }
        )
    finally:
        restart_bridge_if_needed(bridge_was_active)

    report_path = REPORT_DIR / "real-target-repair-enqueue-20260526-r1.json"
    write_json(report_path, report)
    files = [str(report_path.relative_to(ORIS_DIR))]
    for path in [
        RUN_DIR / f"{FAILED_TASK_ID}.failure_result.json",
        TRIAGE_DIR / f"{FAILED_TASK_ID}.json",
        REPAIR_PLAN_DIR / f"{REPAIR_TASK_ID}.json",
    ]:
        if path.exists():
            files.append(str(path.relative_to(ORIS_DIR)))
    run(["git", "add", *files], check=True)
    staged = run(["git", "diff", "--cached", "--quiet"])
    if staged.returncode != 0:
        run(["git", "commit", "-m", "test(dev-employee): validate real-target repair enqueue"], check=True)
        run(["git", "push", "origin", "main"], check=True)
    run(["git", "log", "-1", "--oneline"], check=True)
    print(json.dumps({"ok": report.get("ok"), "report_path": str(report_path)}, ensure_ascii=False, indent=2))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
