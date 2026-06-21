from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProcessResult:
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0
