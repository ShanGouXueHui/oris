from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .git_evidence import EvidenceArtifact, publish_evidence_artifacts
from .models import CheckRecorder, EvidenceTarget, RunState, RuntimeContext


SECRET_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]{12,}", re.IGNORECASE),
)
SENSITIVE_KEYS = {
    "token",
    "password",
    "secret",
    "credential",
    "credentials",
    "authorization",
    "cookie",
    "prompt",
    "message",
    "messages",
    "content",
    "toolarguments",
    "toolresults",
    "old_password",
    "new_password",
    "private_key",
    "api_key",
}


def _summary_payload(
    context: RuntimeContext,
    state: RunState,
    checks: CheckRecorder,
    stamp: str,
    evidence_log: str,
    evidence_json: str,
) -> dict[str, Any]:
    return {
        "task_id": context.task_id,
        "checked_at": stamp,
        "result": state.result,
        "failure_code": state.failure_code or None,
        "selected_policy_mode": state.selected_policy_mode,
        "routing_skill_installed": state.routing_skill_installed,
        "checks": checks.checks,
        "check_summary": {
            "total": len(checks.checks),
            "pass": checks.pass_count,
            "fail": checks.fail_count,
            "not_checked": checks.not_checked_count,
        },
        "direct_tool_calls_pass": state.direct_tool_calls_pass,
        "native_agent_acceptance_pass": state.native_agent_acceptance_pass,
        "telemetry_privacy_pass": state.telemetry_privacy_pass,
        "config_scope_valid": state.config_scope_valid,
        "queue_unchanged": state.queue_unchanged,
        "product_unchanged": state.product_unchanged,
        "write_tools_absent": state.write_tools_absent,
        "rollback": {
            "count": state.rollback_count,
            "healthy": state.rollback_healthy,
        },
        "details": state.details,
        "safety": {
            "product_task_submitted": False,
            "write_tools_added": False,
            "openclaw_reinstalled_or_upgraded": False,
            "secret_values_recorded": False,
            "conversation_content_recorded": False,
        },
        "next_action": state.next_action,
        "evidence": {
            "log_path": evidence_log,
            "json_path": evidence_json,
            "self_commit_sha_omitted_to_prevent_post_commit_log_drift": True,
        },
    }


def _write_log(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        f"task_id={payload['task_id']}",
        f"checked_at={payload['checked_at']}",
        f"result={payload['result']}",
        f"failure_code={payload['failure_code'] or ''}",
        f"selected_policy_mode={payload['selected_policy_mode']}",
        f"routing_skill_installed={'YES' if payload['routing_skill_installed'] else 'NO'}",
    ]
    for check in payload["checks"]:
        lines.append(
            "CHECK|{name}|{status}|{detail}".format(
                name=check["name"],
                status=check["status"],
                detail=check["detail"],
            )
        )
    lines.extend(
        [
            "product_task_submitted=NO",
            "write_tools_added=NO",
            "openclaw_reinstalled_or_upgraded=NO",
            "secret_values_recorded=NO",
            "conversation_content_recorded=NO",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _assert_no_sensitive_keys(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).replace("-", "_").lower()
            compact = normalized.replace("_", "")
            if normalized in SENSITIVE_KEYS or compact in SENSITIVE_KEYS:
                raise RuntimeError("sanitized evidence contains a sensitive key")
            _assert_no_sensitive_keys(child)
    elif isinstance(value, list):
        for child in value:
            _assert_no_sensitive_keys(child)


def _assert_safe(log_path: Path, json_path: Path) -> None:
    for path in (log_path, json_path):
        text = path.read_text(encoding="utf-8", errors="replace")
        if any(pattern.search(text) for pattern in SECRET_PATTERNS):
            raise RuntimeError("sanitized evidence secret pattern scan failed")
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    _assert_no_sensitive_keys(payload)


def publish_evidence(
    context: RuntimeContext,
    state: RunState,
    checks: CheckRecorder,
    stamp: str,
    temp_root: Path,
    target: EvidenceTarget,
) -> tuple[str, str]:
    temp_root.mkdir(parents=True, exist_ok=True)
    filename = f"{target.filename_prefix}-{stamp}"
    evidence_log = (
        target.directory / f"{filename}.log"
    ).relative_to(context.repo_root).as_posix()
    evidence_json = (
        target.directory / f"{filename}.json"
    ).relative_to(context.repo_root).as_posix()
    local_log = temp_root / f"{filename}.log"
    local_json = temp_root / f"{filename}.json"

    payload = _summary_payload(
        context,
        state,
        checks,
        stamp,
        evidence_log,
        evidence_json,
    )
    local_json.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    _write_log(local_log, payload)
    _assert_safe(local_log, local_json)

    commit = publish_evidence_artifacts(
        context.repo_root,
        temp_root,
        (
            EvidenceArtifact(evidence_log, local_log),
            EvidenceArtifact(evidence_json, local_json),
        ),
        f"{target.commit_message_prefix} {stamp}",
    )
    state.evidence_commit = commit
    state.evidence_remote_verified = True
    return evidence_log, evidence_json
