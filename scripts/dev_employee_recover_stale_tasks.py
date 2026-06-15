#!/usr/bin/env python3
"""Recover stale ORIS Dev Employee queue descriptors safely.

Commercial rule: a stale running task is never automatically executed again.
If durable task-run evidence is already terminal, the queue descriptor is
reconciled to that terminal state. Otherwise, an expired lease becomes a
terminal ``failed`` task with failure code ``lease_expired``. A retry must be an
explicit new task id through the intake control plane.

This script does not execute Codex or mutate product repositories.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from dev_employee_queue_kernel import DEFAULT_KERNEL, atomic_write_json, now_iso, read_json
from dev_employee_task_states import canonical_status, is_terminal_status

ORIS_DIR = Path("/home/admin/projects/oris")
QUEUE_DIR = ORIS_DIR / "orchestration/dev_employee_queue"
RUN_DIR = ORIS_DIR / "orchestration/task_runs"
LOG_DIR = ORIS_DIR / "logs/dev_employee"


def reconcile_terminal_run_descriptors() -> dict[str, Any]:
    summary: dict[str, Any] = {"reconciled": [], "skipped": []}
    for path in sorted(QUEUE_DIR.glob("*.running.json")):
        try:
            task = read_json(path)
        except Exception as exc:
            summary["skipped"].append({"path": str(path), "reason": f"invalid_queue_json:{type(exc).__name__}"})
            continue
        task_id = str(task.get("task_id") or path.name.removesuffix(".running.json"))
        run_path = RUN_DIR / f"{task_id}.json"
        if not run_path.exists():
            continue
        try:
            run_state = read_json(run_path)
        except Exception as exc:
            summary["skipped"].append({"task_id": task_id, "reason": f"invalid_run_json:{type(exc).__name__}"})
            continue
        raw_status = str(run_state.get("status") or "unknown")
        canonical = canonical_status(raw_status)
        if not is_terminal_status(canonical):
            continue

        if canonical == "completed":
            suffix = "done"
            task.update(
                {
                    "status": "completed",
                    "canonical_status": "completed",
                    "terminal": True,
                    "reconciled_at": now_iso(),
                    "reconcile_reason": "terminal_task_run_already_completed",
                    "product_commit_sha": run_state.get("product_commit_sha"),
                    "product_remote_sha": run_state.get("product_remote_sha"),
                }
            )
        elif canonical == "cancelled":
            suffix = "cancelled"
            task.update(
                {
                    "status": "cancelled",
                    "canonical_status": "cancelled",
                    "terminal": True,
                    "reconciled_at": now_iso(),
                    "reconcile_reason": "terminal_task_run_cancelled",
                }
            )
        else:
            suffix = "failed"
            task.update(
                {
                    "status": canonical if canonical in {"preflight_failed", "local_checks_failed", "remote_verification_failed", "blocked", "failed", "error"} else "failed",
                    "canonical_status": canonical,
                    "terminal": True,
                    "failure_code": run_state.get("failure_code") or raw_status,
                    "reconciled_at": now_iso(),
                    "reconcile_reason": "terminal_task_run_already_failed",
                }
            )

        target = DEFAULT_KERNEL.task_path(task_id, suffix)
        if target.exists():
            summary["skipped"].append({"task_id": task_id, "reason": "terminal_queue_target_exists", "target": str(target)})
            continue
        atomic_write_json(path, task)
        os.replace(path, target)
        try:
            DEFAULT_KERNEL.release_claim(task_id, str(task.get("lease_token") or ""), terminal_status=canonical)
        except Exception:
            DEFAULT_KERNEL.lock_path(task_id).unlink(missing_ok=True)
            DEFAULT_KERNEL.control_path(task_id, "cancel").unlink(missing_ok=True)
        DEFAULT_KERNEL.append_event(
            task_id,
            "terminal_descriptor_reconciled",
            status=canonical,
            actor="stale-recovery",
            details={"run_path": str(run_path), "target": str(target), "raw_status": raw_status},
        )
        summary["reconciled"].append({"task_id": task_id, "from": str(path), "to": str(target), "status": canonical})
    return summary


def recover(max_age_minutes: int) -> dict[str, Any]:
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    reconciliation = reconcile_terminal_run_descriptors()
    expiry = DEFAULT_KERNEL.expire_stale(fallback_max_age_minutes=max_age_minutes)
    return {
        "checked_at": now_iso(),
        "policy": "terminal_reconcile_else_fail_lease_expired_no_automatic_requeue",
        "max_age_minutes": max_age_minutes,
        "reconciliation": reconciliation,
        "lease_expiry": expiry,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Safely reconcile or expire stale ORIS Dev Employee tasks")
    parser.add_argument("--max-age-minutes", type=int, default=120)
    parser.add_argument(
        "--fail-completed-running",
        action="store_true",
        help="Deprecated compatibility flag; completed task-run evidence is always reconciled to done.",
    )
    args = parser.parse_args()
    summary = recover(max(1, args.max_age_minutes))
    out = LOG_DIR / "stale_task_recovery_latest.json"
    atomic_write_json(out, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
