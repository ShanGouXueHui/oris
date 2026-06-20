from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .clock import now


@dataclass(frozen=True)
class ApprovalRecord:
    approval_id: str
    operation_id: str
    intent_hash: str
    actor_id: str
    approver_id: str
    decision: str
    expires_at: datetime
    policy_version: str

    @property
    def expired(self) -> bool:
        return self.expires_at <= now()

    def validate(self, *, require_separation: bool) -> None:
        if self.decision != "approved":
            raise ValueError("approval decision is not approved")
        if self.expired:
            raise ValueError("approval expired")
        if require_separation and self.actor_id == self.approver_id:
            raise ValueError("approval separation of duties violated")

    def to_dict(self) -> dict[str, Any]:
        return {
            "approval_id": self.approval_id,
            "operation_id": self.operation_id,
            "intent_hash": self.intent_hash,
            "actor_id": self.actor_id,
            "approver_id": self.approver_id,
            "decision": self.decision,
            "expires_at": self.expires_at.isoformat(timespec="seconds"),
            "policy_version": self.policy_version,
        }
