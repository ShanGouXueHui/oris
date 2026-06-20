from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StatusResult:
    status: str
    terminal: bool
    task_id: str | None = None
    operation_id: str | None = None
    details: dict[str, Any] | None = None
