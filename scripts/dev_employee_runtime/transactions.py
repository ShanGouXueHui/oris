from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass
class RollbackTransaction:
    _rollbacks: list[Callable[[], None]] = field(default_factory=list)
    _committed: bool = False

    def add_rollback(self, callback: Callable[[], None]) -> None:
        if self._committed:
            raise RuntimeError("transaction already committed")
        self._rollbacks.append(callback)

    def commit(self) -> None:
        self._committed = True
        self._rollbacks.clear()

    def rollback(self) -> None:
        if self._committed:
            return
        failures: list[Exception] = []
        for callback in reversed(self._rollbacks):
            try:
                callback()
            except Exception as exc:
                failures.append(exc)
        self._rollbacks.clear()
        if failures:
            raise RuntimeError(f"rollback failed in {len(failures)} operation(s)") from failures[0]
