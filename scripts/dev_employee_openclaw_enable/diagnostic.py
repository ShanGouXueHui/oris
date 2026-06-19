from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

from .diagnostic_baseline import (
    DiagnosticBaseline,
    capture_baseline,
    record_final_invariants,
    verify_baseline_unchanged,
)
from .diagnostic_candidate import (
    build_private_candidate,
    candidate_evidence,
    inspect_private_candidate,
)
from .diagnostic_core_selftest import run_core_diagnostic_selftests
from .diagnostic_evidence import publish_diagnostic_evidence
from .engineering_scan import scan_engineering_sources
from .models import CheckRecorder, RunState, RuntimeContext
from .policy import validate_denied_baseline
from .state import sha256_file


SUCCESS_RESULT = "DIAGNOSTIC_CANDIDATE_VALIDATED_PENDING_EVIDENCE_REVIEW"
_STAGE_CHECKS = (
    "diagnostic_selftests",
    "source_authority_and_hardcoding_scan",
    "tools_denied_baseline",
    "gateway_baseline_health",
    "private_candidate_build",
    "candidate_policy_compatibility",
    "installed_runtime_candidate_validation",
    "active_candidate_activation",
    "runtime_plugin_inventory",
    "direct_tool_calls",
    "native_agent_acceptance",
    "telemetry_acceptance",
    "rollback",
    "final_gateway_health",
    "queue_invariant",
    "product_invariant",
)


def _mark_remaining_not_checked(checks: CheckRecorder, reason: str) -> None:
    recorded = {str(item.get("name")) for item in checks.checks}
    for name in _STAGE_CHECKS:
        if name not in recorded:
            checks.not_checked(name, reason)


def _record_post_activation_not_checked(checks: CheckRecorder) -> None:
    checks.not_checked(
        "active_candidate_activation",
        "diagnostic-only run intentionally did not replace active configuration",
    )
    for name in (
        "runtime_plugin_inventory",
        "direct_tool_calls",
        "native_agent_acceptance",
    ):
        checks.not_checked(
            name,
            "requires runtime-accepted active candidate and controlled restart",
        )
    checks.not_checked("telemetry_acceptance", "requires native Agent tool calls")
    checks.not_checked("rollback", "no active mutation occurred")


def _run_pre_activation_checks(
    context: RuntimeContext,
    state: RunState,
    checks: CheckRecorder,
    temp_root: Path,
) -> DiagnosticBaseline:
    if not run_core_diagnostic_selftests():
        checks.fail_check("diagnostic_selftests", "diagnostic selftests failed")
        raise RuntimeError("diagnostic_selftests_failed")
    checks.pass_check("diagnostic_selftests", "diagnostic selftests passed")

    source_scan = scan_engineering_sources(context)
    state.details["engineering_scan"] = source_scan
    if not source_scan.get("ok"):
        checks.fail_check(
            "source_authority_and_hardcoding_scan",
            "duplicate authority or forbidden hardcoding detected",
        )
        raise RuntimeError("engineering_source_scan_failed")
    checks.pass_check(
        "source_authority_and_hardcoding_scan",
        "target source authority and hardcoding scan passed",
    )

    state.details["baseline_policy"] = validate_denied_baseline(context)
    checks.pass_check(
        "tools_denied_baseline",
        "exact approved tools remain denied in the active baseline",
    )

    baseline = capture_baseline(context)
    state.details["gateway_before"] = baseline.service.evidence()
    if not baseline.service.healthy:
        checks.fail_check(
            "gateway_baseline_health",
            "existing Gateway baseline is not healthy",
        )
        raise RuntimeError("gateway_baseline_unhealthy")
    checks.pass_check(
        "gateway_baseline_health",
        "existing Gateway PID and HTTP health captured",
    )

    candidate_path, application = build_private_candidate(context, temp_root)
    state.selected_policy_mode = str(application["mode"])
    state.details["policy_application"] = application
    state.details["candidate"] = candidate_evidence(candidate_path)
    if sha256_file(context.openclaw_config) != baseline.active_config_sha256:
        checks.fail_check(
            "private_candidate_build",
            "active OpenClaw configuration changed during candidate build",
        )
        raise RuntimeError("active_config_changed_during_candidate_build")
    checks.pass_check(
        "private_candidate_build",
        "candidate built in a private temporary path without active mutation",
    )

    compatibility, runtime_validation = inspect_private_candidate(
        context,
        candidate_path,
    )
    state.details["candidate_compatibility"] = compatibility
    state.config_scope_valid = compatibility.get("status") == "PASS"
    if not state.config_scope_valid:
        checks.fail_check(
            "candidate_policy_compatibility",
            "candidate profile, allow, alsoAllow, deny, group, or Skill checks failed",
        )
        raise RuntimeError("candidate_policy_compatibility_failed")
    checks.pass_check(
        "candidate_policy_compatibility",
        "candidate optional-tool and Skill policy are internally consistent",
    )

    state.details["installed_runtime_validation"] = runtime_validation
    validation_status = str(runtime_validation.get("status"))
    if validation_status == "PASS":
        checks.pass_check(
            "installed_runtime_candidate_validation",
            "installed OpenClaw accepted the private candidate through a discovered validator",
        )
        state.result = SUCCESS_RESULT
        state.failure_code = ""
        state.next_action = "READ_GITHUB_DIAGNOSTIC_EVIDENCE_BEFORE_CONTROLLED_ACTIVATION"
    elif validation_status == "FAIL":
        checks.fail_check(
            "installed_runtime_candidate_validation",
            "installed OpenClaw validator rejected the private candidate",
        )
        state.result = "DIAGNOSTIC_RUNTIME_VALIDATION_FAILED"
        state.failure_code = "installed_runtime_candidate_validation_failed"
        state.next_action = "READ_GITHUB_VALIDATION_EVIDENCE_AND_REMEDIATE_REJECTED_FIELDS"
    else:
        checks.not_checked(
            "installed_runtime_candidate_validation",
            "installed CLI exposed no safe alternate-config validator",
        )
        state.result = "DIAGNOSTIC_VALIDATOR_UNAVAILABLE"
        state.failure_code = "candidate_path_validator_not_discovered"
        state.next_action = "READ_GITHUB_CLI_DISCOVERY_EVIDENCE_BEFORE_ANY_ACTIVATION"
    _record_post_activation_not_checked(checks)
    return baseline


def run_policy_diagnostic(
    context: RuntimeContext,
    state: RunState,
    checks: CheckRecorder,
    stamp: str,
) -> tuple[str, str]:
    temp_root = Path(
        tempfile.mkdtemp(prefix=f"oris-readonly-policy-diagnostic-{stamp}-")
    )
    os.chmod(temp_root, 0o700)
    evidence_log = ""
    evidence_json = ""
    baseline: DiagnosticBaseline | None = None
    try:
        baseline = _run_pre_activation_checks(context, state, checks, temp_root)
        record_final_invariants(context, state, checks, baseline)
        state.rollback_healthy = "NOT_REQUIRED"
        state.details["safety_boundaries"] = {
            "diagnostic_only": True,
            "active_config_mutated": False,
            "gateway_restarted": False,
            "product_task_submitted": False,
            "write_tools_added": False,
            "failure_capture_controller_ready": True,
        }
    except Exception as exc:
        if not state.failure_code:
            state.result = "DIAGNOSTIC_FAILED"
            state.failure_code = type(exc).__name__
            state.next_action = "READ_GITHUB_DIAGNOSTIC_EVIDENCE_BEFORE_ANY_RETRY"
        _mark_remaining_not_checked(
            checks,
            "blocked by an earlier diagnostic failure",
        )
        if baseline is not None:
            try:
                state.details["post_failure_baseline"] = verify_baseline_unchanged(
                    context,
                    baseline,
                )
            except Exception:
                state.details["post_failure_baseline"] = {"status": "NOT_CHECKED"}
    finally:
        try:
            commit, evidence_log, evidence_json = publish_diagnostic_evidence(
                context,
                state,
                checks,
                stamp,
                temp_root / "evidence",
            )
            state.evidence_commit = commit
            state.evidence_remote_verified = True
        except Exception as evidence_exc:
            state.details["result_before_evidence_failure"] = state.result
            state.evidence_commit = ""
            state.evidence_remote_verified = False
            state.result = "DIAGNOSTIC_EVIDENCE_PUBLISH_FAILED"
            state.failure_code = type(evidence_exc).__name__
            state.next_action = (
                "FIX_EVIDENCE_PUBLICATION_WITHOUT_REPEATING_RUNTIME_DIAGNOSTIC"
            )
        finally:
            shutil.rmtree(temp_root, ignore_errors=True)
    return evidence_log, evidence_json
