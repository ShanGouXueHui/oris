from __future__ import annotations

from dataclasses import dataclass

from .clock import now_iso


@dataclass(frozen=True)
class CancelRequest:
    task_id: str
    requested_by: str
    reason: str
    requested_at: str

    @classmethod
    def create(cls, *, task_id: str, requested_by: str, reason: str) -> "CancelRequest":
        return cls(task_id, requested_by, reason, now_iso())
