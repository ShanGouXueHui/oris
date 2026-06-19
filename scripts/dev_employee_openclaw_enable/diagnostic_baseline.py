from __future__ import annotations

from dataclasses import dataclass

from .models import CheckRecorder, RepoSnapshot, RunState, RuntimeContext
from .service_control import ServiceSnapshot, service_snapshot
from .state import (
    active_queue_count,
    queue_fingerprint,
    repository_snapshot,
    repository_unchanged,
    sha256_file,
)


@dataclass(frozen=True)
class DiagnosticBaseline:
    service: ServiceSnapshot
    active_config_sha256: str
    queue_fingerprint: str
    active_queue_count: int
    product: RepoSnapshot


def capture_baseline(context: RuntimeContext) -> DiagnosticBaseline:
    return DiagnosticBaseline(
        service=service_snapshot(context),
        active_config_sha256=sha256_file(context.openclaw_config),
        queue_fingerprint=queue_fingerprint(context.repo_root),
        active_queue_count=active_queue_count(context.repo_root),
        product=repository_snapshot(context.product_repo),
    )


def verify_baseline_unchanged(
    context: RuntimeContext,
    baseline: DiagnosticBaseline,
) -> dict[str, object]:
    service = service_snapshot(context)
    config_unchanged = (
        sha256_file(context.openclaw_config) == baseline.active_config_sha256
    )
    queue_unchanged = (
        queue_fingerprint(context.repo_root) == baseline.queue_fingerprint
        and active_queue_count(context.repo_root) == baseline.active_queue_count
    )
    product_unchanged = repository_unchanged(
        baseline.product,
        repository_snapshot(context.product_repo),
    )
    return {
        "gateway": service.evidence(),
        "gateway_healthy": service.healthy,
        "active_config_unchanged": config_unchanged,
        "queue_unchanged": queue_unchanged,
        "product_unchanged": product_unchanged,
        "all_unchanged": bool(
            service.healthy
            and config_unchanged
            and queue_unchanged
            and product_unchanged
        ),
    }


def record_final_invariants(
    context: RuntimeContext,
    state: RunState,
    checks: CheckRecorder,
    baseline: DiagnosticBaseline,
) -> None:
    final = verify_baseline_unchanged(context, baseline)
    state.details["final_baseline"] = final
    state.queue_unchanged = bool(final["queue_unchanged"])
    state.product_unchanged = bool(final["product_unchanged"])
    if final["gateway_healthy"] and final["active_config_unchanged"]:
        checks.pass_check(
            "final_gateway_health",
            "Gateway remained healthy on the exact tools-denied active config",
        )
    else:
        checks.fail_check("final_gateway_health", "Gateway health or active config changed")
    if state.queue_unchanged:
        checks.pass_check("queue_invariant", "queue state remained unchanged")
    else:
        checks.fail_check("queue_invariant", "queue changed during diagnostic")
    if state.product_unchanged:
        checks.pass_check("product_invariant", "product repository remained unchanged")
    else:
        checks.fail_check("product_invariant", "product repository changed during diagnostic")
    if not final["all_unchanged"]:
        raise RuntimeError("diagnostic_changed_runtime_baseline")
