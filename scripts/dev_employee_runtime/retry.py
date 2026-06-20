from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RetryRequest:
    original_task_id: str
    retry_task_id: str
    requested_by: str
    reason: str
    original_terminal_status: str

    def validate(self) -> None:
        if self.original_terminal_status not in {"failed", "cancelled"}:
            raise ValueError("retry requires an explicit failed or cancelled terminal task")
        if self.original_task_id == self.retry_task_id:
            raise ValueError("retry must use a new task id")
