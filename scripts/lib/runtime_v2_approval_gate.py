from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from runtime_v2_run_store import RuntimeV2RunStore, utc_now


class ApprovalGateError(Exception):
    pass


class ApprovalNotFoundError(ApprovalGateError):
    pass


class ApprovalGateStore:
    def __init__(self, path: Path | str, run_store: RuntimeV2RunStore) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.run_store = run_store
        if not self.path.exists():
            self._write({"approvals": {}, "decisions": []})

    def _read(self) -> Dict[str, Any]:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, data: Dict[str, Any]) -> None:
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        os.replace(tmp, self.path)

    def create_request(self, run_id: str, action_type: str, risk_level: str, reason: str, evidence_ref: Optional[str] = None, idempotency_key: Optional[str] = None) -> Dict[str, Any]:
        data = self._read()
        if idempotency_key:
            for approval in data["approvals"].values():
                if approval.get("idempotency_key") == idempotency_key:
                    return approval
        approval_id = str(uuid.uuid4())
        approval = {
            "approval_id": approval_id,
            "run_id": run_id,
            "status": "PENDING",
            "risk_level": risk_level,
            "action_type": action_type,
            "reason": reason,
            "evidence_ref": evidence_ref,
            "idempotency_key": idempotency_key,
            "created_at": utc_now(),
            "decided_at": None,
        }
        data["approvals"][approval_id] = approval
        data["decisions"].append({"approval_id": approval_id, "decision": "REQUESTED", "actor": "runtime", "comment": reason, "decided_at": approval["created_at"]})
        self._write(data)
        return approval

    def get_request(self, approval_id: str) -> Dict[str, Any]:
        data = self._read()
        if approval_id not in data["approvals"]:
            raise ApprovalNotFoundError(approval_id)
        return data["approvals"][approval_id]

    def decide(self, approval_id: str, decision: str, actor: str, comment: str = "") -> Dict[str, Any]:
        data = self._read()
        if approval_id not in data["approvals"]:
            raise ApprovalNotFoundError(approval_id)
        approval = data["approvals"][approval_id]
        if approval["status"] != "PENDING":
            return approval
        now = utc_now()
        approval["decided_at"] = now
        normalized = decision.upper()
        if normalized == "APPROVE":
            approval["status"] = "APPROVED"
            self.run_store.transition_run(approval["run_id"], "RUNNING", actor=actor, reason="approval_approved")
        elif normalized == "REJECT":
            approval["status"] = "REJECTED"
            self.run_store.transition_run(approval["run_id"], "FAILED_BLOCKED", actor=actor, reason="approval_rejected")
        elif normalized == "EXPIRE":
            approval["status"] = "EXPIRED"
            self.run_store.transition_run(approval["run_id"], "FAILED_BLOCKED", actor=actor, reason="approval_expired")
        else:
            raise ApprovalGateError(f"unknown decision: {decision}")
        data["decisions"].append({"approval_id": approval_id, "decision": normalized, "actor": actor, "comment": comment, "decided_at": now})
        self._write(data)
        return approval

    def create_issue_payload(self, approval_id: str) -> Dict[str, Any]:
        approval = self.get_request(approval_id)
        title = f"Approval required: {approval['action_type']} for run {approval['run_id']}"
        body = (
            f"Risk level: {approval['risk_level']}\n\n"
            f"Reason: {approval['reason']}\n\n"
            f"Evidence: `{approval.get('evidence_ref')}`\n\n"
            "Decision options: APPROVE, REJECT, EXPIRE"
        )
        return {"title": title, "body": body, "approval_id": approval_id, "run_id": approval["run_id"]}

    def create_request_from_worker_result(self, run_id: str, worker_result: Dict[str, Any], action_type: str = "unknown_high_risk_action") -> Dict[str, Any]:
        if worker_result.get("status") != "WAITING_APPROVAL":
            raise ApprovalGateError("worker result is not waiting for approval")
        return self.create_request(
            run_id=run_id,
            action_type=action_type,
            risk_level="HIGH",
            reason=worker_result.get("decision", "approval_required"),
            evidence_ref=worker_result.get("evidence_ref"),
            idempotency_key=f"approval:{run_id}:{action_type}",
        )
