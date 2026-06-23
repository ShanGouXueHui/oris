from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from runtime_v2_run_store import utc_now


class ExecutorPolicyError(Exception):
    pass


class DeniedActionError(ExecutorPolicyError):
    pass


DEFAULT_ALLOWED_ACTIONS = {
    "noop",
    "write_evidence",
    "fail_retryable",
    "fail_fatal",
    "require_approval",
}


class RuntimeV2Executor:
    def __init__(self, evidence_dir: Path | str, allowed_actions: Optional[Iterable[str]] = None) -> None:
        self.evidence_dir = Path(evidence_dir)
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        self.allowed_actions = set(allowed_actions or DEFAULT_ALLOWED_ACTIONS)

    def execute(self, action: Dict[str, Any]) -> Dict[str, Any]:
        action_type = action.get("action_type", "")
        payload = action.get("payload", {})
        risk_level = action.get("risk_level", "LOW")

        if action_type not in self.allowed_actions:
            artifact_ref = self._write_artifact(action_type or "unknown", "DENIED", {"reason": "action_not_allowed"})
            return {
                "status": "DENIED",
                "outcome_type": "denied",
                "evidence_ref": artifact_ref,
                "message": f"action denied: {action_type}",
            }

        if risk_level == "HIGH" and action_type != "require_approval":
            artifact_ref = self._write_artifact(action_type, "APPROVAL_REQUIRED", {"reason": "high_risk_action"})
            return {
                "status": "APPROVAL_REQUIRED",
                "outcome_type": "approval_required",
                "evidence_ref": artifact_ref,
                "message": "high-risk action requires approval",
            }

        if action_type == "noop":
            artifact_ref = self._write_artifact(action_type, "SUCCEEDED", {"payload": payload})
            return {"status": "SUCCEEDED", "outcome_type": "success", "evidence_ref": artifact_ref, "message": "noop completed"}

        if action_type == "write_evidence":
            artifact_ref = self._write_artifact(action_type, "SUCCEEDED", {"payload": payload})
            return {"status": "SUCCEEDED", "outcome_type": "success", "evidence_ref": artifact_ref, "message": "evidence written"}

        if action_type == "fail_retryable":
            artifact_ref = self._write_artifact(action_type, "RETRYABLE_FAILED", {"reason": payload.get("reason", "retryable_failure")})
            return {"status": "RETRYABLE_FAILED", "outcome_type": "retryable", "evidence_ref": artifact_ref, "message": "retryable failure"}

        if action_type == "fail_fatal":
            artifact_ref = self._write_artifact(action_type, "FATAL_FAILED", {"reason": payload.get("reason", "fatal_failure")})
            return {"status": "FATAL_FAILED", "outcome_type": "fatal", "evidence_ref": artifact_ref, "message": "fatal failure"}

        if action_type == "require_approval":
            artifact_ref = self._write_artifact(action_type, "APPROVAL_REQUIRED", {"reason": payload.get("reason", "approval_required")})
            return {"status": "APPROVAL_REQUIRED", "outcome_type": "approval_required", "evidence_ref": artifact_ref, "message": "approval required"}

        artifact_ref = self._write_artifact(action_type, "FATAL_FAILED", {"reason": "unhandled_allowed_action"})
        return {"status": "FATAL_FAILED", "outcome_type": "fatal", "evidence_ref": artifact_ref, "message": "unhandled allowed action"}

    def as_worker_executor(self, action: Dict[str, Any]):
        def _executor(run: Dict[str, Any], attempt: int) -> Dict[str, Any]:
            result = self.execute(action)
            outcome_type = result["outcome_type"]
            if outcome_type == "denied":
                return {"type": "fatal", "reason": result["message"], "evidence_ref": result["evidence_ref"]}
            if outcome_type == "approval_required":
                return {"type": "approval_required", "reason": result["message"], "evidence_ref": result["evidence_ref"]}
            if outcome_type == "retryable":
                return {"type": "retryable", "reason": result["message"], "evidence_ref": result["evidence_ref"]}
            if outcome_type == "fatal":
                return {"type": "fatal", "reason": result["message"], "evidence_ref": result["evidence_ref"]}
            return {"type": "success", "evidence_ref": result["evidence_ref"]}
        return _executor

    def _write_artifact(self, action_type: str, status: str, payload_summary: Dict[str, Any]) -> str:
        artifact_id = str(uuid.uuid4())
        artifact = {
            "artifact_id": artifact_id,
            "action_type": action_type,
            "status": status,
            "created_at": utc_now(),
            "payload_summary": payload_summary,
        }
        path = self.evidence_dir / f"{artifact_id}.json"
        path.write_text(json.dumps(artifact, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        return str(path)
