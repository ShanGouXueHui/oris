#!/usr/bin/env python3
"""Transactional filesystem queue kernel for ORIS Dev Employee.

The filesystem remains the current operational store, but all lifecycle mutations
must go through this module. It provides atomic JSON writes, per-task claim locks,
leases and heartbeats, cancellation controls, an append-only event ledger,
idempotency fingerprints, explicit retry ids, and safe stale-task expiry.

This is intentionally database-compatible: task descriptors and events carry the
same fields that a later SQL-backed task/event store will own.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import socket
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

DEFAULT_ORIS_DIR = Path("/home/admin/projects/oris")
DEFAULT_QUEUE_DIR = DEFAULT_ORIS_DIR / "orchestration/dev_employee_queue"
DEFAULT_EVENT_DIR = DEFAULT_ORIS_DIR / "orchestration/dev_employee_events"
DEFAULT_CONTROL_DIR = DEFAULT_ORIS_DIR / "orchestration/dev_employee_controls"
DEFAULT_LOCK_DIR = DEFAULT_ORIS_DIR / "run/dev_employee_queue_locks"

TERMINAL_SUFFIXES = ("done", "failed", "cancelled")
ACTIVE_SUFFIXES = ("queued", "running")


class QueueKernelError(RuntimeError):
    """Base lifecycle error."""


class TaskConflict(QueueKernelError):
    """The requested mutation conflicts with existing task state."""


class TaskNotFound(QueueKernelError):
    """No task record exists for the requested task id."""


class LeaseMismatch(QueueKernelError):
    """A worker attempted to mutate a lease it does not own."""


def now() -> datetime:
    return datetime.now(timezone.utc).astimezone()


def now_iso() -> str:
    return now().isoformat(timespec="seconds")


def parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc).astimezone()
    return parsed


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def request_fingerprint(payload: dict[str, Any]) -> str:
    """Return a stable idempotency fingerprint without secret or runtime fields."""
    normalized = {
        "project_key": str(payload.get("project_key") or "").strip(),
        "objective": str(payload.get("objective") or "").strip(),
        "constraints": [str(item).strip() for item in payload.get("constraints") or [] if str(item).strip()],
        "expected_checks": [str(item).strip() for item in payload.get("expected_checks") or [] if str(item).strip()],
        "commit_message": str(payload.get("commit_message") or "").strip(),
        "retry_of": str(payload.get("retry_of") or "").strip() or None,
        "attempt": int(payload.get("attempt") or 1),
    }
    return hashlib.sha256(canonical_json(normalized).encode("utf-8")).hexdigest()


def default_worker_id() -> str:
    return f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:12]}"


def pid_alive(pid: Any) -> bool:
    try:
        value = int(pid)
    except (TypeError, ValueError):
        return False
    if value <= 0:
        return False
    try:
        os.kill(value, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / f".{path.name}.{uuid.uuid4().hex}.tmp"
    encoded = (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb", closefd=True) as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if temporary.exists():
            temporary.unlink(missing_ok=True)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


@dataclass(frozen=True)
class ClaimResult:
    path: Path
    task_id: str
    lease_token: str
    worker_id: str
    execution_deadline_at: str


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

    def heartbeat(
        self,
        task_id: str,
        lease_token: str,
        *,
        phase: str | None = None,
        lease_seconds: int = 60,
    ) -> dict[str, Any]:
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
        records = self.existing_records(task_id)
        for suffix in TERMINAL_SUFFIXES:
            if suffix in records:
                return {"task_id": task_id, "status": suffix, "terminal": True, "idempotent": True}

        queued = records.get("queued")
        if queued:
            token = uuid.uuid4().hex
            try:
                self._create_claim_lock(task_id, f"cancel:{requested_by}", token)
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
                        cancelled = self.task_path(task_id, "cancelled")
                        os.replace(queued, cancelled)
                        self.append_event(task_id, "task_cancelled", status="cancelled", actor=requested_by, details={"reason": reason, "stage": "queued"})
                        return {"task_id": task_id, "status": "cancelled", "terminal": True, "path": str(cancelled)}
                finally:
                    self._release_claim_lock(task_id, token)

        running = self.task_path(task_id, "running")
        if running.exists():
            control = {
                "task_id": task_id,
                "requested_at": now_iso(),
                "requested_by": requested_by,
                "reason": reason,
            }
            path = self.control_path(task_id, "cancel")
            if path.exists():
                existing = read_json(path)
                return {"task_id": task_id, "status": "cancel_requested", "terminal": False, "idempotent": True, "control": existing}
            atomic_write_json(path, control)
            self.append_event(task_id, "cancel_requested", status="cancelling", actor=requested_by, details={"reason": reason})
            return {"task_id": task_id, "status": "cancel_requested", "terminal": False, "control": control}

        raise TaskNotFound(f"no active or terminal queue record for {task_id}")

    def release_claim(self, task_id: str, lease_token: str, *, terminal_status: str) -> None:
        self._release_claim_lock(task_id, lease_token)
        self.control_path(task_id, "cancel").unlink(missing_ok=True)
        self.append_event(task_id, "claim_released", status=terminal_status, details={"terminal_status": terminal_status})

    def expire_stale(self, *, fallback_max_age_minutes: int = 120) -> dict[str, Any]:
        summary: dict[str, Any] = {"checked_at": now_iso(), "expired": [], "skipped": []}
        current = now()
        fallback_delta = timedelta(minutes=max(1, fallback_max_age_minutes))
        for path in sorted(self.queue_dir.glob("*.running.json")):
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
            target = self.task_path(task_id, "failed")
            if target.exists():
                summary["skipped"].append({"task_id": task_id, "reason": "terminal_target_exists", "path": str(target)})
                continue
            os.replace(path, target)
            self._release_claim_lock(task_id, task.get("lease_token"))
            self.control_path(task_id, "cancel").unlink(missing_ok=True)
            self.append_event(task_id, "lease_expired", status="failed", details=task["failure_details"])
            summary["expired"].append({"task_id": task_id, "from": str(path), "to": str(target), "failure_code": "lease_expired"})
        return summary

    def lifecycle_summary(self, task_id: str) -> dict[str, Any]:
        records = self.existing_records(task_id)
        running = read_json(records["running"]) if "running" in records else None
        cancel = self.cancel_request(task_id)
        return {
            "records": {suffix: str(path) for suffix, path in records.items()},
            "lease": {
                key: running.get(key)
                for key in ["worker_id", "worker_pid", "lease_token", "claimed_at", "heartbeat_at", "lease_expires_at", "execution_deadline_at", "phase", "attempt", "max_attempts"]
            }
            if running
            else None,
            "cancel_request": cancel,
            "event_ledger": str(self.event_path(task_id)) if self.event_path(task_id).exists() else None,
        }


def generate_retry_task_id(original_task_id: str, existing_task_ids: Iterable[str]) -> str:
    existing = set(existing_task_ids)
    for attempt in range(1, 1000):
        candidate = f"{original_task_id}-r{attempt}"
        if candidate not in existing:
            return candidate
    raise TaskConflict(f"unable to allocate retry id for {original_task_id}")


DEFAULT_KERNEL = QueueKernel()
