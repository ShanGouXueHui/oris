from __future__ import annotations

import fcntl
import hashlib
import json
import os
import uuid
from datetime import timedelta
from pathlib import Path
from typing import Any

from dev_employee_runtime.clock import now, now_iso
from dev_employee_runtime.json_store import atomic_write_json, canonical_json, read_json
from dev_employee_runtime.queue_cancel import request_cancel as apply_cancel_request
from dev_employee_runtime.queue_lifecycle import expire_stale as apply_expire_stale
from dev_employee_runtime.queue_lifecycle import lifecycle_summary as build_lifecycle_summary
from dev_employee_runtime.queue_paths import DEFAULT_CONTROL_DIR, DEFAULT_EVENT_DIR, DEFAULT_LOCK_DIR, DEFAULT_QUEUE_DIR
from dev_employee_runtime.queue_types import ACTIVE_SUFFIXES, TERMINAL_SUFFIXES, ClaimResult, LeaseMismatch, TaskNotFound


class QueueKernel:
    def __init__(
        self,
        queue_dir: Path = DEFAULT_QUEUE_DIR,
        event_dir: Path = DEFAULT_EVENT_DIR,
        control_dir: Path = DEFAULT_CONTROL_DIR,
        lock_dir: Path = DEFAULT_LOCK_DIR,
    ) -> None:
        self.queue_dir = Path(queue_dir)
        self.event_dir = Path(event_dir)
        self.control_dir = Path(control_dir)
        self.lock_dir = Path(lock_dir)
        for directory in [self.queue_dir, self.event_dir, self.control_dir, self.lock_dir]:
            directory.mkdir(parents=True, exist_ok=True)

    def task_path(self, task_id: str, suffix: str) -> Path:
        return self.queue_dir / f"{task_id}.{suffix}.json"

    def control_path(self, task_id: str, control: str) -> Path:
        return self.control_dir / f"{task_id}.{control}.json"

    def lock_path(self, task_id: str) -> Path:
        return self.lock_dir / f"{task_id}.claim.lock.json"

    def event_path(self, task_id: str) -> Path:
        return self.event_dir / f"{task_id}.jsonl"

    def append_event(
        self,
        task_id: str,
        event_type: str,
        *,
        status: str | None = None,
        actor: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        event = {
            "event_id": uuid.uuid4().hex,
            "task_id": task_id,
            "event_type": event_type,
            "status": status,
            "actor": actor,
            "occurred_at": now_iso(),
            "details": details or {},
        }
        path = self.event_path(task_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            os.write(fd, (canonical_json(event) + "\n").encode("utf-8"))
            os.fsync(fd)
        finally:
            try:
                fcntl.flock(fd, fcntl.LOCK_UN)
            finally:
                os.close(fd)
        return event

    def existing_records(self, task_id: str) -> dict[str, Path]:
        result: dict[str, Path] = {}
        for suffix in (*ACTIVE_SUFFIXES, *TERMINAL_SUFFIXES):
            path = self.task_path(task_id, suffix)
            if path.exists():
                result[suffix] = path
        return result

    def _create_claim_lock(self, task_id: str, worker_id: str, lease_token: str) -> Path:
        path = self.lock_path(task_id)
        payload = {
            "task_id": task_id,
            "worker_id": worker_id,
            "worker_pid": os.getpid(),
            "lease_token": lease_token,
            "created_at": now_iso(),
        }
        encoded = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            os.write(fd, encoded)
            os.fsync(fd)
        finally:
            os.close(fd)
        return path

    def _release_claim_lock(self, task_id: str, lease_token: str | None = None) -> None:
        path = self.lock_path(task_id)
        if not path.exists():
            return
        if lease_token:
            try:
                current = read_json(path)
            except Exception:
                current = {}
            if current.get("lease_token") not in {None, lease_token}:
                raise LeaseMismatch(f"claim lock token mismatch for {task_id}")
        path.unlink(missing_ok=True)

    def claim(
        self,
        queued_path: Path,
        *,
        worker_id: str,
        lease_seconds: int = 60,
        execution_timeout_seconds: int = 3600,
    ) -> ClaimResult | None:
        try:
            task = read_json(queued_path)
        except (FileNotFoundError, json.JSONDecodeError):
            return None
        task_id = str(task.get("task_id") or "").strip()
        if not task_id or task.get("status") != "queued":
            return None
        if any(self.task_path(task_id, suffix).exists() for suffix in TERMINAL_SUFFIXES):
            return None

        lease_token = uuid.uuid4().hex
        try:
            self._create_claim_lock(task_id, worker_id, lease_token)
        except FileExistsError:
            return None

        running_path = self.task_path(task_id, "running")
        try:
            if running_path.exists() or not queued_path.exists():
                self._release_claim_lock(task_id, lease_token)
                return None
            os.replace(queued_path, running_path)
            current = now()
            deadline = current + timedelta(seconds=max(60, execution_timeout_seconds))
            lease_expiry = current + timedelta(seconds=max(15, lease_seconds))
            task.update(
                {
                    "status": "running",
                    "phase": "claimed",
                    "worker_id": worker_id,
                    "worker_pid": os.getpid(),
                    "lease_token": lease_token,
                    "claimed_at": current.isoformat(timespec="seconds"),
                    "heartbeat_at": current.isoformat(timespec="seconds"),
                    "lease_expires_at": lease_expiry.isoformat(timespec="seconds"),
                    "execution_deadline_at": deadline.isoformat(timespec="seconds"),
                    "attempt": int(task.get("attempt") or 1),
                    "max_attempts": int(task.get("max_attempts") or 3),
                }
            )
            atomic_write_json(running_path, task)
            self.append_event(
                task_id,
                "task_claimed",
                status="claimed",
                actor=worker_id,
                details={
                    "lease_token_hash": hashlib.sha256(lease_token.encode()).hexdigest(),
                    "lease_expires_at": task["lease_expires_at"],
                    "execution_deadline_at": task["execution_deadline_at"],
                    "attempt": task["attempt"],
                },
            )
            return ClaimResult(running_path, task_id, lease_token, worker_id, task["execution_deadline_at"])
        except Exception:
            self._release_claim_lock(task_id, lease_token)
            raise

    def heartbeat(self, task_id: str, lease_token: str, *, phase: str | None = None, lease_seconds: int = 60) -> dict[str, Any]:
        path = self.task_path(task_id, "running")
        if not path.exists():
            raise TaskNotFound(f"running task not found: {task_id}")
        task = read_json(path)
        if task.get("lease_token") != lease_token:
            raise LeaseMismatch(f"lease token mismatch for {task_id}")
        previous_phase = task.get("phase")
        current = now()
        task["heartbeat_at"] = current.isoformat(timespec="seconds")
        task["lease_expires_at"] = (current + timedelta(seconds=max(15, lease_seconds))).isoformat(timespec="seconds")
        if phase:
            task["phase"] = phase
        atomic_write_json(path, task)
        cancel = self.cancel_request(task_id)
        if phase and phase != previous_phase:
            self.append_event(task_id, "phase_changed", status=phase, actor=task.get("worker_id"), details={"from": previous_phase, "to": phase})
        return {"task": task, "cancel_requested": bool(cancel), "cancel": cancel}

    def cancel_request(self, task_id: str) -> dict[str, Any] | None:
        path = self.control_path(task_id, "cancel")
        if not path.exists():
            return None
        try:
            return read_json(path)
        except Exception:
            return {"task_id": task_id, "reason": "invalid_cancel_control"}

    def request_cancel(self, task_id: str, *, requested_by: str, reason: str = "operator_requested") -> dict[str, Any]:
        return apply_cancel_request(self, task_id, requested_by=requested_by, reason=reason)

    def release_claim(self, task_id: str, lease_token: str, *, terminal_status: str) -> None:
        self._release_claim_lock(task_id, lease_token)
        self.control_path(task_id, "cancel").unlink(missing_ok=True)
        self.append_event(task_id, "claim_released", status=terminal_status, details={"terminal_status": terminal_status})

    def expire_stale(self, *, fallback_max_age_minutes: int = 120) -> dict[str, Any]:
        return apply_expire_stale(self, fallback_max_age_minutes=fallback_max_age_minutes)

    def lifecycle_summary(self, task_id: str) -> dict[str, Any]:
        return build_lifecycle_summary(self, task_id)


DEFAULT_KERNEL = QueueKernel()
