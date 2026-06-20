from __future__ import annotations

import os
import shutil
from pathlib import Path

from .gateway_http import select_safe_baseline_tool, verify_public_routes
from .models import CheckRecorder, RepoSnapshot, RuntimeContext
from .policy import validate_denied_baseline
from .process import run
from .state import (
    active_queue_count,
    listener_is_loopback_only,
    load_json,
    queue_fingerprint,
    repository_is_clean,
    repository_snapshot,
)
from .worktree import (
    SourceWorktreeSnapshot,
    source_worktree_is_clean,
    source_worktree_is_synced,
    source_worktree_snapshot,
)


REQUIRED_COMMANDS = ("git", "openclaw", "systemctl", "ss")


def _require_commands() -> None:
    missing = [name for name in REQUIRED_COMMANDS if shutil.which(name) is None]
    if missing:
        raise RuntimeError("required commands are missing: " + ",".join(missing))


def _require_private_file(path: Path) -> None:
    if not path.is_file():
        raise RuntimeError(f"required private file is missing: {path.name}")
    stat = path.stat()
    if stat.st_uid != os.getuid() or (stat.st_mode & 0o777) != 0o600:
        raise RuntimeError(f"private file ownership or mode is invalid: {path.name}")


def _gateway_active(context: RuntimeContext) -> bool:
    result = run(["systemctl", "--user", "is-active", context.gateway_service])
    return result.returncode == 0 and result.stdout.strip() == "active"


def run_transaction_preflight(
    context: RuntimeContext,
    checks: CheckRecorder,
) -> tuple[str, str, RepoSnapshot, SourceWorktreeSnapshot]:
    _require_commands()
    _require_private_file(context.openclaw_config)
    _require_private_file(context.marker_file)
    if not context.product_repo.is_dir():
        raise RuntimeError("baseline product repository is missing")
    readiness = load_json(context.readiness_evidence)
    if readiness.get("result") != "READY":
        raise RuntimeError("authoritative readiness evidence is not READY")
    checks.pass_check("authoritative_readiness", "latest READY evidence verified")

    validate_denied_baseline(context)
    checks.pass_check(
        "tools_denied_baseline",
        "approved tools remain denied before mutation",
    )
    if not _gateway_active(context):
        raise RuntimeError("existing OpenClaw Gateway is not active")
    if not verify_public_routes(context)["ok"]:
        raise RuntimeError("public native UI or restricted route contract failed")
    checks.pass_check(
        "gateway_and_routes",
        "existing Gateway and native public root are healthy",
    )

    if not all(listener_is_loopback_only(port) for port in context.internal_ports):
        raise RuntimeError("an internal ORIS listener is not loopback-only")
    checks.pass_check(
        "private_internal_listeners",
        "required ORIS listeners are loopback-only",
    )

    queue_before = queue_fingerprint(context.repo_root)
    if active_queue_count(context.repo_root) != 0:
        raise RuntimeError("active ORIS product task exists")
    checks.pass_check(
        "queue_baseline",
        "zero active tasks and queue fingerprint captured",
    )

    product_before = repository_snapshot(context.product_repo)
    if not (
        product_before.head == context.expected_product_commit
        and product_before.remote_main == context.expected_product_commit
        and repository_is_clean(product_before)
    ):
        raise RuntimeError(
            "product repository baseline differs from authoritative configuration"
        )
    checks.pass_check(
        "product_baseline",
        "product HEAD, remote main, and clean worktree verified",
    )

    oris_before = source_worktree_snapshot(context.repo_root)
    if not source_worktree_is_synced(oris_before):
        raise RuntimeError("ORIS source HEAD differs from remote main")
    if not source_worktree_is_clean(oris_before):
        raise RuntimeError(
            "ORIS source worktree is not clean "
            f"(count={oris_before.dirty_count},digest={oris_before.dirty_sha256})"
        )
    checks.pass_check(
        "oris_source_baseline",
        "ORIS source worktree clean; configured runtime artifacts excluded",
    )

    baseline_tool = select_safe_baseline_tool(context)
    checks.pass_check(
        "safe_builtin_baseline",
        "safe built-in tool is accessible before mutation",
    )
    return queue_before, baseline_tool, product_before, oris_before
