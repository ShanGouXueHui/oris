from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ActivationState:
    registered: bool
    enabled: bool

    def require_offline(self) -> None:
        if self.registered or self.enabled:
            raise RuntimeError("typed write actions must remain unregistered and disabled")
