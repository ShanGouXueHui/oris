from __future__ import annotations

from pathlib import Path

from dev_employee_runtime.paths import discover_repo_root

DEFAULT_ORIS_DIR = discover_repo_root()
DEFAULT_QUEUE_DIR = DEFAULT_ORIS_DIR / "orchestration" / "dev_employee_queue"
DEFAULT_EVENT_DIR = DEFAULT_ORIS_DIR / "orchestration" / "dev_employee_events"
DEFAULT_CONTROL_DIR = DEFAULT_ORIS_DIR / "orchestration" / "dev_employee_controls"
DEFAULT_LOCK_DIR = DEFAULT_ORIS_DIR / "run" / "dev_employee_queue_locks"


def queue_path(root: Path = DEFAULT_ORIS_DIR) -> Path:
    return root / "orchestration" / "dev_employee_queue"


def event_path(root: Path = DEFAULT_ORIS_DIR) -> Path:
    return root / "orchestration" / "dev_employee_events"


def control_path(root: Path = DEFAULT_ORIS_DIR) -> Path:
    return root / "orchestration" / "dev_employee_controls"


def lock_path(root: Path = DEFAULT_ORIS_DIR) -> Path:
    return root / "run" / "dev_employee_queue_locks"
