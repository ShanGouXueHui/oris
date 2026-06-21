from __future__ import annotations

import hashlib
import os
import socket
import uuid
from datetime import datetime, timezone
from typing import Any, Iterable

from dev_employee_runtime.json_store import canonical_json
from dev_employee_runtime.queue_types import TaskConflict


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


def request_fingerprint(payload: dict[str, Any]) -> str:
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


def generate_retry_task_id(original_task_id: str, existing_task_ids: Iterable[str]) -> str:
    existing = set(existing_task_ids)
    for attempt in range(1, 1000):
        candidate = f"{original_task_id}-r{attempt}"
        if candidate not in existing:
            return candidate
    raise TaskConflict(f"unable to allocate retry id for {original_task_id}")


__all__ = [
    "default_worker_id",
    "generate_retry_task_id",
    "parse_dt",
    "pid_alive",
    "request_fingerprint",
]
