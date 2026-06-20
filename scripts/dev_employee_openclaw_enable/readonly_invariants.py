from __future__ import annotations

from dataclasses import dataclass

from .models import CheckRecorder, RepoSnapshot, RunState, RuntimeContext
from .state import (
    active_queue_count,
    listener_is_loopback_only,
    queue_fingerprint,
    repository_snapshot,
    repository_unchanged,
)


@dataclass(frozen=True)
class ReadonlyInvariantResult:
    queue_unchanged: bool
    product_unchanged: bool
    listeners_private: bool

    @property
    def ok(self) -> bool:
        return self.queue_unchanged and self.product_unchanged and self.listeners_private


def queue_is_unchanged(context: RuntimeContext, baseline: str) -> bool:
    return (
        queue_fingerprint(context.repo_root) == baseline
        and active_queue_count(context.repo_root) == 0
    )


def product_is_unchanged(context: RuntimeContext, baseline: RepoSnapshot) -> bool:
    return repository_unchanged(
        baseline,
        repository_snapshot(context.product_repo),
    )


def listeners_are_private(context: RuntimeContext) -> bool:
    return all(listener_is_loopback_only(port) for port in context.internal_ports)


def evaluate_readonly_invariants(
    context: RuntimeContext,
    queue_before: str,
    product_before: RepoSnapshot,
) -> ReadonlyInvariantResult:
    return ReadonlyInvariantResult(
        queue_unchanged=queue_is_unchanged(context, queue_before),
        product_unchanged=product_is_unchanged(context, product_before),
        listeners_private=listeners_are_private(context),
    )


def record_readonly_invariants(
    state: RunState,
    checks: CheckRecorder,
    result: ReadonlyInvariantResult,
) -> None:
    state.queue_unchanged = result.queue_unchanged
    state.product_unchanged = result.product_unchanged

    recorder = checks.pass_check if result.queue_unchanged else checks.fail_check
    recorder(
        "final_queue_invariant",
        "queue remained unchanged" if result.queue_unchanged else "queue changed",
    )
    recorder = checks.pass_check if result.product_unchanged else checks.fail_check
    recorder(
        "final_product_invariant",
        (
            "product repository remained unchanged"
            if result.product_unchanged
            else "product repository changed"
        ),
    )
    recorder = checks.pass_check if result.listeners_private else checks.fail_check
    recorder(
        "final_listener_invariant",
        (
            "internal listeners remained loopback-only"
            if result.listeners_private
            else "an internal listener became public"
        ),
    )
