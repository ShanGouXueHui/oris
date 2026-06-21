from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ActionResult:
    ok: bool
    code: str
    operation_id: str | None = None
    task_id: str | None = None
    payload: dict[str, Any] | None = None
