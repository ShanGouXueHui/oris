from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TypedQueueDescriptor:
    task_id: str
    project_key: str
    action: str
    operation_id: str
    intent_hash: str
    status: str
    attempt: int
    max_attempts: int
    data: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "project_key": self.project_key,
            "action": self.action,
            "operation_id": self.operation_id,
            "intent_hash": self.intent_hash,
            "status": self.status,
            "attempt": self.attempt,
            "max_attempts": self.max_attempts,
            "data": dict(self.data),
        }
