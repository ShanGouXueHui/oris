from __future__ import annotations

import os
import uuid
from typing import Any

from dev_employee_runtime.clock import now_iso
from dev_employee_runtime.json_store import atomic_write_json, read_json
from dev_employee_runtime.queue_types import TERMINAL_SUFFIXES, TaskNotFound


def request_cancel(kernel: Any, task_id: str, *, requested_by: str, reason: str = "operator_requested") -> dict[str, Any]:
    records = kernel.existing_records(task_id)
    for suffix in TERMINAL_SUFFIXES:
        if suffix in records:
            return {"task_id": task_id, "status": suffix, "terminal": True, "idempotent": True}

    queued = records.get("queued")
    if queued:
        token = uuid.uuid4().hex
        try:
            kernel._create_claim_lock(task_id, f"cancel:{requested_by}", token)
        except FileExistsError:
            queued = None
        else:
            try:
                if queued.exists():
                    task = read_json(queued)
                    task.update(
                        {
                            "status": "cancelled",
                            "canonical_status": "cancelled",
                            "terminal": True,
                            "cancelled_at": now_iso(),
                            "cancelled_by": requested_by,
                            "cancel_reason": reason,
                        }
                    )
                    atomic_write_json(queued, task)
                    cancelled = kernel.task_path(task_id, "cancelled")
                    os.replace(queued, cancelled)
                    kernel.append_event(
                        task_id,
                        "task_cancelled",
                        status="cancelled",
                        actor=requested_by,
                        details={"reason": reason, "stage": "queued"},
                    )
                    return {"task_id": task_id, "status": "cancelled", "terminal": True, "path": str(cancelled)}
            finally:
                kernel._release_claim_lock(task_id, token)

    running = kernel.task_path(task_id, "running")
    if running.exists():
        control = {
            "task_id": task_id,
            "requested_at": now_iso(),
            "requested_by": requested_by,
            "reason": reason,
        }
        path = kernel.control_path(task_id, "cancel")
        if path.exists():
            existing = read_json(path)
            return {"task_id": task_id, "status": "cancel_requested", "terminal": False, "idempotent": True, "control": existing}
        atomic_write_json(path, control)
        kernel.append_event(task_id, "cancel_requested", status="cancelling", actor=requested_by, details={"reason": reason})
        return {"task_id": task_id, "status": "cancel_requested", "terminal": False, "control": control}

    raise TaskNotFound(f"no active or terminal queue record for {task_id}")
