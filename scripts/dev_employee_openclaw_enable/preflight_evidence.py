from __future__ import annotations

import json
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .context import discover_repo_root
from .process import run


EVIDENCE_DIRECTORY = Path("logs/dev_employee/openclaw_readonly_preflight")
SAFE_KEYS = (
    "result",
    "failure_stage",
    "failure_type",
    "context_loaded",
    "python_compiled",
    "readiness_evidence_ready",
    "tools_denied_baseline",
    "agent_cli_supported",
    "gateway_transport_supported",
    "skill_install_target_ready",
    "routing_skill_source_valid",
    "plugin_runtime_ok",
    "public_routes_ok",
    "internal_listeners_private",
    "source_worktree_ready",
    "source_worktree_head_synced",
    "source_worktree_dirty_count",
    "source_worktree_dirty_sha256",
    "source_worktree_dirty_paths",
    "source_worktree_dirty_paths_truncated",
    "source_files_modified",
    "config_mutated",
    "gateway_restarted",
    "secret_values_recorded",
)


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("preflight result must contain a JSON object")
    return value


def _safe_payload(source: dict[str, Any], stamp: str) -> dict[str, Any]:
    payload = {key: source.get(key) for key in SAFE_KEYS}
    dirty_paths = payload.get("source_worktree_dirty_paths")
    if not isinstance(dirty_paths, list) or not all(
        isinstance(item, str) for item in dirty_paths
    ):
        payload["source_worktree_dirty_paths"] = []
    payload["recorded_at"] = stamp
    payload["safety"] = {
        "secret_values_recorded": False,
        "conversation_content_recorded": False,
        "config_mutated_by_evidence_writer": False,
        "gateway_restarted_by_evidence_writer": False,
    }
    return payload


def _write_result(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def commit_preflight_evidence(
    repo_root: Path,
    source_path: Path,
) -> dict[str, Any]:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    source = _read_json(source_path)
    payload = _safe_payload(source, stamp)
    evidence_name = f"openclaw-readonly-preflight-{stamp}.json"
    evidence_rel = (EVIDENCE_DIRECTORY / evidence_name).as_posix()

    temp_root = Path(tempfile.mkdtemp(prefix=f"oris-preflight-evidence-{stamp}-"))
    worktree = temp_root / "worktree"
    local_evidence = temp_root / evidence_name
    try:
        _write_result(local_evidence, payload)
        fetched = run(["git", "fetch", "origin", "main"], cwd=repo_root, timeout=90)
        if fetched.returncode != 0:
            raise RuntimeError("preflight evidence fetch failed")
        added = run(
            ["git", "worktree", "add", "--detach", str(worktree), "origin/main"],
            cwd=repo_root,
            timeout=90,
        )
        if added.returncode != 0:
            raise RuntimeError("preflight evidence worktree creation failed")
        destination = worktree / evidence_rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(local_evidence, destination)
        if run(["git", "add", "--", evidence_rel], cwd=worktree).returncode != 0:
            raise RuntimeError("preflight evidence staging failed")
        if run(["git", "diff", "--cached", "--check"], cwd=worktree).returncode != 0:
            raise RuntimeError("preflight evidence diff validation failed")
        committed = run(
            [
                "git",
                "commit",
                "-m",
                f"chore(dev-employee): record OpenClaw preflight {stamp}",
            ],
            cwd=worktree,
            timeout=90,
        )
        if committed.returncode != 0:
            raise RuntimeError("preflight evidence commit failed")
        if run(["git", "fetch", "origin", "main"], cwd=worktree, timeout=90).returncode != 0:
            raise RuntimeError("preflight evidence refetch failed")
        merge_base = run(["git", "merge-base", "HEAD", "origin/main"], cwd=worktree)
        remote_ref = run(["git", "rev-parse", "origin/main"], cwd=worktree)
        if merge_base.stdout.strip() != remote_ref.stdout.strip():
            rebased = run(["git", "rebase", "origin/main"], cwd=worktree, timeout=90)
            if rebased.returncode != 0:
                raise RuntimeError("preflight evidence rebase failed")
        commit = run(["git", "rev-parse", "HEAD"], cwd=worktree)
        pushed = run(["git", "push", "origin", "HEAD:main"], cwd=worktree, timeout=120)
        if commit.returncode != 0 or pushed.returncode != 0:
            raise RuntimeError("preflight evidence push failed")
        remote = run(
            ["git", "ls-remote", "--heads", "origin", "refs/heads/main"],
            cwd=worktree,
            timeout=60,
        )
        remote_sha = remote.stdout.split()[0] if remote.stdout.split() else ""
        commit_sha = commit.stdout.strip()
        if not commit_sha or commit_sha != remote_sha:
            raise RuntimeError("preflight evidence remote SHA mismatch")
        return {
            "result": "COMMITTED",
            "evidence_path": evidence_rel,
            "evidence_commit": commit_sha,
            "evidence_remote_verified": True,
            "secret_values_recorded": False,
        }
    finally:
        if worktree.exists():
            run(
                ["git", "worktree", "remove", "--force", str(worktree)],
                cwd=repo_root,
            )
        shutil.rmtree(temp_root, ignore_errors=True)


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: preflight_evidence.py <preflight.json> <result.json>", file=sys.stderr)
        return 64
    repo_root = discover_repo_root()
    source_path = Path(sys.argv[1]).expanduser().resolve()
    result_path = Path(sys.argv[2]).expanduser().resolve()
    try:
        result = commit_preflight_evidence(repo_root, source_path)
        _write_result(result_path, result)
        return 0
    except Exception as exc:
        _write_result(
            result_path,
            {
                "result": "FAILED",
                "failure_type": type(exc).__name__,
                "evidence_remote_verified": False,
                "secret_values_recorded": False,
            },
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
