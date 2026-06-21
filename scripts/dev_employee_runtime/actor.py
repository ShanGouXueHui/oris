from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ActorContext:
    actor_id: str
    roles: tuple[str, ...]
    source: str

    def validate(self) -> None:
        if not self.actor_id.strip():
            raise ValueError("actor_id is required")
        if not self.roles:
            raise ValueError("at least one actor role is required")
        if not self.source.strip():
            raise ValueError("actor source is required")
