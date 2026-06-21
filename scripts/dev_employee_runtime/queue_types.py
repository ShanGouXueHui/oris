from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

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


@dataclass(frozen=True)
class ClaimResult:
    path: Path
    task_id: str
    lease_token: str
    worker_id: str
    execution_deadline_at: str
