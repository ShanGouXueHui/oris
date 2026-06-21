from __future__ import annotations

import uuid
from datetime import timedelta
from pathlib import Path
from typing import Any

from dev_employee_runtime.approval import ApprovalRecord
from dev_employee_runtime.audit import stable_hash
from dev_employee_runtime.cancel import CancelRequest
from dev_employee_runtime.clock import now, now_iso
from dev_employee_runtime.events import append_event
from dev_employee_runtime.idempotency import request_fingerprint
from dev_employee_runtime.json_store import atomic_write_json, read_json
from dev_employee_runtime.operation import PreparedOperation
from dev_employee_runtime.project_auth import authorize_project_action
from dev_employee_runtime.rbac import evaluate_permission
from dev_employee_runtime.retry import RetryRequest
from dev_employee_runtime.scope import authorize_relative_path
from dev_employee_runtime.typed_write_policy import TypedWritePolicy, load_typed_write_policy


class TypedWriteService:
    def __init__(self, policy: TypedWritePolicy | None = None) -> None:
        self.policy = policy or load_typed_write_policy()
        self.policy.activation.require_offline()
        self.policy.storage.initialize()

    @property
    def root(self) -> Path:
        return self.policy.storage.root

    def _event(self, operation_id: str, event_type: str, actor_id: str, details: dict[str, Any]) -> None:
        append_event(
            self.policy.storage.audit / "typed_write.jsonl",
            task_id=operation_id,
            event_type=event_type,
            status=details.get("status"),
            actor_id=actor_id,
            details=details,
        )

    def _validate_payload_keys(self, payload: dict[str, Any], allowed: tuple[str, ...]) -> None:
        extra = sorted(set(payload) - set(allowed))
        if extra:
            raise PermissionError(f"payload contains unsupported keys: {extra}")

    def _validate_paths(self, payload: dict[str, Any], project_key: str) -> None:
        paths = payload.get("paths") or []
        if not isinstance(paths, list):
            raise ValueError("payload paths must be a list")
        project = self.policy.project(project_key)
        for value in paths:
            authorize_relative_path(
                str(value),
                allowed_scopes=project.allowed_scopes,
                forbidden_scopes=project.forbidden_scopes,
            )

    def prepare(self, *, actor_id: str, actor_roles: tuple[str, ...], project_key: str, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.policy.activation.require_offline()
        action_policy = self.policy.action(action)
        project_policy = self.policy.project(project_key)
        rbac = evaluate_permission(actor_roles, action_policy.permission, self.policy.role_permissions)
        if not rbac.allowed:
            raise PermissionError(rbac.reason)
        project_auth = authorize_project_action(
            project_key=project_key,
            action=action,
            allowed_actions=project_policy.allowed_actions,
        )
        if not project_auth.allowed:
            raise PermissionError(project_auth.reason)
        self._validate_payload_keys(payload, action_policy.allowed_payload_keys)
        self._validate_paths(payload, project_key)

        fingerprint = request_fingerprint(
            {
                "action": action,
                "actor_id": actor_id,
                "project_key": project_key,
                "payload": payload,
                "policy_version": self.policy.policy_version,
            }
        )
        index_path = self.policy.storage.idempotency / f"{fingerprint}.json"
        if index_path.exists():
            existing = read_json(index_path)
            return read_json(self.policy.storage.prepared / f"{existing['operation_id']}.json")

        prepared_at = now()
        operation_id = "op-" + uuid.uuid4().hex
        operation = PreparedOperation.create(
            operation_id=operation_id,
            action=action,
            actor_id=actor_id,
            project_key=project_key,
            risk_tier=action_policy.risk_tier,
            payload=payload,
            prepared_at=prepared_at,
            expires_at=prepared_at + timedelta(seconds=action_policy.approval_ttl_seconds),
            policy_version=self.policy.policy_version,
            approval_required=action_policy.approval_required,
        )
        operation_dict = operation.to_dict()
        atomic_write_json(self.policy.storage.prepared / f"{operation_id}.json", operation_dict)
        atomic_write_json(index_path, {"operation_id": operation_id, "fingerprint": fingerprint})
        self._event(operation_id, "typed_write_prepared", actor_id, {"status": "prepared", "action": action, "risk_tier": action_policy.risk_tier, "payload": payload})
        return operation_dict

    def approve(self, *, operation_id: str, approver_id: str, approver_roles: tuple[str, ...]) -> dict[str, Any]:
        op = read_json(self.policy.storage.prepared / f"{operation_id}.json")
        decision = evaluate_permission(approver_roles, "typed_write.approve", self.policy.role_permissions)
        if not decision.allowed:
            raise PermissionError(decision.reason)
        approval = ApprovalRecord(
            approval_id="appr-" + uuid.uuid4().hex,
            operation_id=operation_id,
            intent_hash=str(op["intent_hash"]),
            actor_id=str(op["actor_id"]),
            approver_id=approver_id,
            decision="approved",
            expires_at=now() + timedelta(seconds=900),
            policy_version=str(op["policy_version"]),
        )
        approval.validate(require_separation=self.policy.require_approval_separation)
        data = approval.to_dict()
        atomic_write_json(self.policy.storage.approvals / f"{operation_id}.json", data)
        self._event(operation_id, "typed_write_approved", approver_id, {"status": "approved", "approval_id": approval.approval_id})
        return data

    def finalize_prepared(self, *, operation_id: str, actor_id: str) -> dict[str, Any]:
        op = read_json(self.policy.storage.prepared / f"{operation_id}.json")
        if op.get("approval_required"):
            approval_data = read_json(self.policy.storage.approvals / f"{operation_id}.json")
            approval = ApprovalRecord(
                approval_id=str(approval_data["approval_id"]),
                operation_id=str(approval_data["operation_id"]),
                intent_hash=str(approval_data["intent_hash"]),
                actor_id=str(approval_data["actor_id"]),
                approver_id=str(approval_data["approver_id"]),
                decision=str(approval_data["decision"]),
                expires_at=now().fromisoformat(str(approval_data["expires_at"])),
                policy_version=str(approval_data["policy_version"]),
            )
            approval.validate(require_separation=self.policy.require_approval_separation)
            if approval.intent_hash != op["intent_hash"] or approval.policy_version != op["policy_version"]:
                raise ValueError("approval does not match prepared operation")
        target = self.root / "committed" / f"{operation_id}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            return read_json(target)
        record = {
            "operation_id": operation_id,
            "state": "prepared_for_manual_handoff",
            "finalized_at": now_iso(),
            "finalized_by": actor_id,
            "operation_hash": stable_hash(op),
            "runtime_dispatch": False,
            "product_mutation": False,
        }
        atomic_write_json(target, record)
        self._event(operation_id, "typed_write_finalized_offline", actor_id, {"status": "finalized", "runtime_dispatch": False})
        return record

    def cancel_operation(self, *, operation_id: str, actor_id: str, reason: str) -> dict[str, Any]:
        request = CancelRequest.create(task_id=operation_id, requested_by=actor_id, reason=reason)
        path = self.root / "cancel_requests" / f"{operation_id}.json"
        atomic_write_json(path, request.__dict__)
        self._event(operation_id, "typed_write_cancel_requested", actor_id, {"status": "cancel_requested", "reason": reason})
        return read_json(path)

    def retry_terminal_task(self, *, original_task_id: str, retry_task_id: str, actor_id: str, reason: str, original_terminal_status: str) -> dict[str, Any]:
        request = RetryRequest(original_task_id, retry_task_id, actor_id, reason, original_terminal_status)
        request.validate()
        path = self.root / "retry_requests" / f"{retry_task_id}.json"
        data = request.__dict__ | {"requested_at": now_iso()}
        atomic_write_json(path, data)
        self._event(retry_task_id, "typed_write_retry_requested", actor_id, {"status": "retry_requested", "original_task_id": original_task_id})
        return read_json(path)


def runtime_dispatch(*_args: Any, **_kwargs: Any) -> None:
    raise RuntimeError("typed write runtime dispatch is not registered or enabled")
