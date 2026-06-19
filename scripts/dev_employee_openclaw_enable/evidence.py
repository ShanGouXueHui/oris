from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

from .models import CheckRecorder, RunState, RuntimeContext
from .process import run


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
        "checks": checks.checks,
        "check_summary": {
            "total": len(checks.checks),
            "pass": checks.pass_count,
            "fail": checks.fail_count,
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


def write_and_commit_evidence(
    context: RuntimeContext,
    state: RunState,
    checks: CheckRecorder,
    stamp: str,
    temp_root: Path,
) -> tuple[str, str, str]:
    temp_root.mkdir(parents=True, exist_ok=True)
    filename = f"openclaw-readonly-automatic-enablement-{stamp}"
    evidence_log = (context.evidence_directory / f"{filename}.log").relative_to(context.repo_root).as_posix()
    evidence_json = (context.evidence_directory / f"{filename}.json").relative_to(context.repo_root).as_posix()
    local_log = temp_root / f"{filename}.log"
    local_json = temp_root / f"{filename}.json"
    payload = _summary_payload(context, state, checks, stamp, evidence_log, evidence_json)
    local_json.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    _write_log(local_log, payload)
    _assert_safe(local_log, local_json)

    fetched = run(["git", "fetch", "origin", "main"], cwd=context.repo_root, timeout=90)
    if fetched.returncode != 0:
        raise RuntimeError("unable to fetch ORIS main for evidence")
    worktree = temp_root / "evidence-worktree"
    added = run(
        ["git", "worktree", "add", "--detach", str(worktree), "origin/main"],
        cwd=context.repo_root,
        timeout=90,
    )
    if added.returncode != 0:
        raise RuntimeError("unable to create detached evidence worktree")
    try:
        destination_log = worktree / evidence_log
        destination_json = worktree / evidence_json
        destination_log.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(local_log, destination_log)
        shutil.copy2(local_json, destination_json)
        staged = run(["git", "add", "--", evidence_log, evidence_json], cwd=worktree)
        checked = run(["git", "diff", "--cached", "--check"], cwd=worktree)
        if staged.returncode != 0 or checked.returncode != 0:
            raise RuntimeError("evidence staging validation failed")
        committed = run(
            ["git", "commit", "-m", f"{context.evidence_commit_prefix} {stamp}"],
            cwd=worktree,
            timeout=90,
        )
        if committed.returncode != 0:
            raise RuntimeError("evidence commit failed")
        refreshed = run(["git", "fetch", "origin", "main"], cwd=worktree, timeout=90)
        if refreshed.returncode != 0:
            raise RuntimeError("evidence refetch failed")
        merge_base = run(["git", "merge-base", "HEAD", "origin/main"], cwd=worktree)
        remote_ref = run(["git", "rev-parse", "origin/main"], cwd=worktree)
        if merge_base.stdout.strip() != remote_ref.stdout.strip():
            rebased = run(["git", "rebase", "origin/main"], cwd=worktree, timeout=90)
            if rebased.returncode != 0:
                raise RuntimeError("evidence rebase failed")
        commit = run(["git", "rev-parse", "HEAD"], cwd=worktree)
        pushed = run(["git", "push", "origin", "HEAD:main"], cwd=worktree, timeout=120)
        if commit.returncode != 0 or pushed.returncode != 0:
            raise RuntimeError("evidence push failed")
        remote = run(
            ["git", "ls-remote", "--heads", "origin", "refs/heads/main"],
            cwd=worktree,
            timeout=60,
        )
        remote_sha = remote.stdout.split()[0] if remote.stdout.split() else ""
        commit_sha = commit.stdout.strip()
        if not commit_sha or remote_sha != commit_sha:
            raise RuntimeError("evidence remote SHA mismatch")
        return commit_sha, evidence_log, evidence_json
    finally:
        run(["git", "worktree", "remove", "--force", str(worktree)], cwd=context.repo_root)
