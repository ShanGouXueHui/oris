from __future__ import annotations

from .gateway_http import verify_public_routes
from .models import RunState, RuntimeContext
from .plugin_runtime import verify_plugin_runtime
from .policy import PolicyApplication, PolicyBackup, validate_config_scope
from .state import listener_is_loopback_only
from .worktree import (
    SourceWorktreeSnapshot,
    source_worktree_snapshot,
    source_worktree_unchanged,
)


def verify_runtime_boundaries(
    context: RuntimeContext,
    state: RunState,
    backup: PolicyBackup,
    application: PolicyApplication,
    oris_snapshot: SourceWorktreeSnapshot,
) -> None:
    validate_config_scope(context, backup, application)
    runtime = verify_plugin_runtime(context)
    if not runtime.get("ok") or runtime.get("write_tools"):
        raise RuntimeError("final plugin runtime contract failed")
    if not all(listener_is_loopback_only(port) for port in context.internal_ports):
        raise RuntimeError("an internal listener exposure changed")
    if not verify_public_routes(context)["ok"]:
        raise RuntimeError("final public route contract failed")
    if not source_worktree_unchanged(
        oris_snapshot,
        source_worktree_snapshot(context.repo_root),
    ):
        raise RuntimeError("ORIS source worktree changed before evidence commit")
