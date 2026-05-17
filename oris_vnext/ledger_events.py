"""Append-only ledger event helpers for ORIS Dev Employee."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ALLOWED_RUN_STATES = {
    "planned",
    "bootstrap_checked",
    "validated",
    "blocked",
    "running",
    "error",
    "done",
}


@dataclass(frozen=True)
class LedgerEvent:
    """Small status event appended beside task_run records."""

    task_run_id: str
    event_type: str
    state: str
    created_at: str
    reason: str
    previous_state: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json_line(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, sort_keys=True)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_state_event(
    *,
    task_run_id: str,
    state: str,
    reason: str,
    previous_state: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> LedgerEvent:
    if state not in ALLOWED_RUN_STATES:
        raise ValueError(f"invalid state: {state}")
    if previous_state is not None and previous_state not in ALLOWED_RUN_STATES:
        raise ValueError(f"invalid previous_state: {previous_state}")
    return LedgerEvent(
        task_run_id=task_run_id,
        event_type="task_state_event",
        state=state,
        previous_state=previous_state,
        created_at=utc_now(),
        reason=reason,
        metadata=metadata or {},
    )


def append_event(path: str | Path, event: LedgerEvent) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as fp:
        fp.write(event.to_json_line() + "\n")
