from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Any, Mapping

from .audit import stable_hash


@dataclass(frozen=True)
class PreparedOperation:
    operation_id: str
    action: str
    actor_id: str
    project_key: str
    risk_tier: str
    payload: Mapping[str, Any]
    intent_hash: str
    prepared_at: datetime
    expires_at: datetime
    policy_version: str
    approval_required: bool

    @classmethod
    def create(
        cls,
        *,
        operation_id: str,
        action: str,
        actor_id: str,
        project_key: str,
        risk_tier: str,
        payload: dict[str, Any],
        prepared_at: datetime,
        expires_at: datetime,
        policy_version: str,
        approval_required: bool,
    ) -> "PreparedOperation":
        immutable_payload = MappingProxyType(dict(payload))
        intent = {
            "action": action,
            "actor_id": actor_id,
            "project_key": project_key,
            "risk_tier": risk_tier,
            "payload": dict(immutable_payload),
            "policy_version": policy_version,
        }
        return cls(
            operation_id=operation_id,
            action=action,
            actor_id=actor_id,
            project_key=project_key,
            risk_tier=risk_tier,
            payload=immutable_payload,
            intent_hash=stable_hash(intent),
            prepared_at=prepared_at,
            expires_at=expires_at,
            policy_version=policy_version,
            approval_required=approval_required,
        )

    @property
    def expired(self) -> bool:
        from .clock import now

        return self.expires_at <= now()

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation_id": self.operation_id,
            "action": self.action,
            "actor_id": self.actor_id,
            "project_key": self.project_key,
            "risk_tier": self.risk_tier,
            "payload": dict(self.payload),
            "intent_hash": self.intent_hash,
            "prepared_at": self.prepared_at.isoformat(timespec="seconds"),
            "expires_at": self.expires_at.isoformat(timespec="seconds"),
            "policy_version": self.policy_version,
            "approval_required": self.approval_required,
        }
