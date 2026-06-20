from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StorageLayout:
    root: Path

    @property
    def prepared(self) -> Path:
        return self.root / "prepared"

    @property
    def approvals(self) -> Path:
        return self.root / "approvals"

    @property
    def idempotency(self) -> Path:
        return self.root / "idempotency"

    @property
    def audit(self) -> Path:
        return self.root / "audit"

    @property
    def locks(self) -> Path:
        return self.root / "locks"

    def initialize(self) -> None:
        for path in (self.prepared, self.approvals, self.idempotency, self.audit, self.locks):
            path.mkdir(parents=True, exist_ok=True)
