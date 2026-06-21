from __future__ import annotations

import os
import socket
from datetime import timedelta
from typing import Any

from dev_employee_runtime.clock import now, now_iso
from dev_employee_runtime.json_store import atomic_write_json, read_json
from dev_employee_runtime.queue_utils import parse_dt, pid_alive


def expire_stale(kernel: Any, *, fallback_max_age_minutes: int = 120) -> dict[str, Any]:
    summary: dict[str, Any] = {"checked_at": now_iso(), "expired": [], "skipped": []}
    current = now()
    fallback_delta = timedelta(minutes=max(1, fallback_max_age_minutes))
    for path in sorted(kernel.queue_dir.glob("*.running.json")):
        try:
            task = read_json(path)
        except Exception as exc:
            summary["skipped"].append({"path": str(path), "reason": f"invalid_json:{type(exc).__name__}"})
            continue
        task_id = str(task.get("task_id") or path.name.removesuffix(".running.json"))
        lease_expiry = parse_dt(task.get("lease_expires_at"))
        if lease_expiry is None:
            reference = parse_dt(task.get("heartbeat_at") or task.get("claimed_at") or task.get("started_at"))
            lease_expiry = reference + fallback_delta if reference else None
        if lease_expiry is None or lease_expiry > current:
            summary["skipped"].append({"task_id": task_id, "reason": "lease_active_or_missing_reference"})
            continue
        if task.get("worker_id", "").startswith(socket.gethostname() + ":") and pid_alive(task.get("worker_pid")):
            summary["skipped"].append({"task_id": task_id, "reason": "owner_process_alive", "worker_pid": task.get("worker_pid")})
            continue
        task.update(
            {
                "status": "failed",
                "canonical_status": "failed",
                "terminal": True,
                "failure_code": "lease_expired",
                "failed_at": now_iso(),
                "failure_details": {
                    "lease_expires_at": task.get("lease_expires_at"),
                    "heartbeat_at": task.get("heartbeat_at"),
                    "worker_id": task.get("worker_id"),
                    "worker_pid": task.get("worker_pid"),
                },
            }
        )
        atomic_write_json(path, task)
        target = kernel.task_path(task_id, "failed")
        if target.exists():
            summary["skipped"].append({"task_id": task_id, "reason": "terminal_target_exists", "path": str(target)})
            continue
        os.replace(path, target)
        kernel._release_claim_lock(task_id, task.get("lease_token"))
        kernel.control_path(task_id, "cancel").unlink(missing_ok=True)
        kernel.append_event(task_id, "lease_expired", status="failed", details=task["failure_details"])
        summary["expired"].append({"task_id": task_id, "from": str(path), "to": str(target), "failure_code": "lease_expired"})
    return summary


def lifecycle_summary(kernel: Any, task_id: str) -> dict[str, Any]:
    records = kernel.existing_records(task_id)
    running = read_json(records["running"]) if "running" in records else None
    cancel = kernel.cancel_request(task_id)
    return {
        "records": {suffix: str(path) for suffix, path in records.items()},
        "lease": {
            key: running.get(key)
            for key in [
                "worker_id",
                "worker_pid",
                "lease_token",
                "claimed_at",
                "heartbeat_at",
                "lease_expires_at",
                "execution_deadline_at",
                "phase",
                "attempt",
                "max_attempts",
            ]
        }
        if running
        else None,
        "cancel_request": cancel,
        "event_ledger": str(kernel.event_path(task_id)) if kernel.event_path(task_id).exists() else None,
    }
