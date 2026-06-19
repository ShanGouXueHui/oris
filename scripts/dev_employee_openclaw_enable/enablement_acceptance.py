from __future__ import annotations

from .agent_acceptance import run_automatic_acceptance
from .models import CheckRecorder, RepoSnapshot, RunState, RuntimeContext
from .policy import PolicyApplication, PolicyBackup, finalize_marker
from .runtime_boundaries import verify_runtime_boundaries
from .state import (
    active_queue_count,
    queue_fingerprint,
    repository_snapshot,
    repository_unchanged,
)
from .worktree import SourceWorktreeSnapshot


def run_native_acceptance(
    context: RuntimeContext,
    state: RunState,
    checks: CheckRecorder,
    stamp: str,
    queue_before: str,
) -> None:
    automatic = run_automatic_acceptance(context, stamp)
    state.details["native_agent_acceptance"] = automatic
    if not automatic.get("accepted"):
        state.native_agent_acceptance_pass = False
        raise RuntimeError(
            str(
                automatic.get("reason")
                or "automatic native agent acceptance failed"
            )
        )
    state.native_agent_acceptance_pass = True
    telemetry = automatic.get("telemetry") or {}
    state.telemetry_privacy_pass = bool(
        telemetry.get("schema_ok")
        and telemetry.get("content_safe")
        and telemetry.get("only_approved_tools_used")
    )
    if not state.telemetry_privacy_pass:
        raise RuntimeError(
            "telemetry privacy, schema, or approved-tool validation failed"
        )
    checks.pass_check(
        "automatic_native_agent_acceptance",
        "three natural-language turns completed automatically",
    )
    checks.pass_check(
        "telemetry_privacy",
        "typed hook telemetry is private, schema-safe, and read-only",
    )

    if (
        queue_fingerprint(context.repo_root) != queue_before
        or active_queue_count(context.repo_root) != 0
    ):
        state.queue_unchanged = False
        raise RuntimeError("queue changed during native agent acceptance")
    state.queue_unchanged = True
    checks.pass_check(
        "final_queue_invariant",
        "queue fingerprint and active count are unchanged",
    )


def verify_final_invariants(
    context: RuntimeContext,
    state: RunState,
    checks: CheckRecorder,
    product_before: RepoSnapshot,
    oris_before: SourceWorktreeSnapshot,
    policy_backup: PolicyBackup,
    application: PolicyApplication,
) -> None:
    if not repository_unchanged(
        product_before,
        repository_snapshot(context.product_repo),
    ):
        state.product_unchanged = False
        raise RuntimeError("product repository changed during read-only acceptance")
    state.product_unchanged = True
    checks.pass_check(
        "final_product_invariant",
        "product repository is unchanged",
    )

    verify_runtime_boundaries(
        context,
        state,
        policy_backup,
        application,
        oris_before,
    )
    checks.pass_check(
        "final_runtime_and_route_invariants",
        "runtime, routes, listeners, and source worktree verified",
    )


def finalize_enablement(
    context: RuntimeContext,
    state: RunState,
    checks: CheckRecorder,
    policy_backup: PolicyBackup,
    application: PolicyApplication,
    stamp: str,
) -> None:
    finalize_marker(
        context,
        policy_backup,
        application,
        stamp,
    )
    checks.pass_check(
        "private_marker",
        "automatic read-only acceptance recorded privately",
    )
