from __future__ import annotations

import tempfile
from dataclasses import replace
from pathlib import Path

from .activation_transaction import activate_validated_candidate
from .agent_acceptance import run_automatic_acceptance
from .agent_skill_policy import resolve_default_agent_id
from .effective_surface_inventory import probe_approved_effective_tool_surface
from .enablement_rollback import run_enablement_rollback
from .evidence import publish_evidence
from .model_tool_diagnostic_contract import ModelToolDiagnosticContract
from .model_tool_diagnostic_result import classify_model_tool_diagnostic
from .models import CheckRecorder, RepoSnapshot, RunState, RuntimeContext
from .plugin_runtime import verify_plugin_runtime
from .policy import PolicyBackup
from .preflight_checks import run_transaction_preflight
from .readonly_invariants import evaluate_readonly_invariants, record_readonly_invariants
from .skill_installation import SkillBackup
from .state import load_json


def diagnostic_context(
    context: RuntimeContext,
    contract: ModelToolDiagnosticContract,
    control_tool: str,
) -> RuntimeContext:
    oris_tool = str(contract.oris_turn.expected_tool)
    turns = (
        {
            "intent": contract.control_turn.intent,
            "expected_tool": control_tool,
            "message_template": contract.control_turn.message_template.format(
                tool_name=control_tool
            ),
        },
        {
            "intent": contract.oris_turn.intent,
            "expected_tool": oris_tool,
            "message_template": contract.oris_turn.message_template,
        },
    )
    return replace(
        context,
        approved_tools=(control_tool, oris_tool),
        acceptance_turns=turns,
        session_prefix=contract.session_prefix,
        turn_timeout_seconds=contract.turn_timeout_seconds,
        telemetry_wait_seconds=contract.telemetry_wait_seconds,
    )


def _rollback_check(state: RunState, checks: CheckRecorder) -> None:
    if state.rollback_healthy == "YES":
        checks.pass_check(
            "model_tool_diagnostic_rollback",
            "exact tools-denied baseline and healthy Gateway restored",
        )
        return
    checks.fail_check(
        "model_tool_diagnostic_rollback",
        "rollback did not restore the healthy tools-denied baseline",
    )


def _verify_runtime(context: RuntimeContext, state: RunState, checks: CheckRecorder) -> None:
    runtime = verify_plugin_runtime(context)
    state.write_tools_absent = not bool(runtime.get("write_tools"))
    if not runtime.get("ok") or not state.write_tools_absent:
        raise RuntimeError("plugin runtime contract failed")
    checks.pass_check(
        "model_tool_plugin_runtime",
        "read-only Plugin tools and hooks verified",
    )
    agent_id = resolve_default_agent_id(load_json(context.openclaw_config))
    surface = probe_approved_effective_tool_surface(
        context,
        context.direct_probe_session_key,
        agent_id,
    )
    state.details["effective_tool_surface"] = surface
    if surface.get("status") != "PASS":
        raise RuntimeError("effective tool surface regressed")
    checks.pass_check(
        "effective_tool_surface",
        "approved ORIS tools remain present and plugin-owned",
    )


def _publish(
    context: RuntimeContext,
    contract: ModelToolDiagnosticContract,
    state: RunState,
    checks: CheckRecorder,
    stamp: str,
) -> tuple[str, str]:
    return publish_evidence(
        context,
        state,
        checks,
        stamp,
        Path(tempfile.mkdtemp(prefix=f"oris-model-tool-{stamp}-")),
        contract.evidence,
    )


def run_model_tool_diagnostic(
    context: RuntimeContext,
    contract: ModelToolDiagnosticContract,
    state: RunState,
    checks: CheckRecorder,
    stamp: str,
) -> tuple[str, str]:
    policy_backup: PolicyBackup | None = None
    skill_backup: SkillBackup | None = None
    queue_before = ""
    product_before: RepoSnapshot | None = None
    evidence_log = ""
    evidence_json = ""
    try:
        queue_before, control_tool, product_before, _ = run_transaction_preflight(
            context,
            checks,
            probe_safe_builtin=True,
        )
        state.direct_tool_calls_pass = True
        activation = activate_validated_candidate(context, state, checks, stamp)
        policy_backup = activation.policy_backup
        skill_backup = activation.skill_backup
        _verify_runtime(context, state, checks)
        automatic = run_automatic_acceptance(
            diagnostic_context(context, contract, control_tool),
            stamp,
        )
        classify_model_tool_diagnostic(
            state,
            checks,
            automatic,
            control_tool,
            str(contract.oris_turn.expected_tool),
        )
    except Exception as exc:
        state.result = "MODEL_TOOL_DIAGNOSTIC_FAILED"
        state.failure_code = type(exc).__name__
        state.next_action = "READ_MODEL_TOOL_DIAGNOSTIC_FAILURE_EVIDENCE"
        checks.fail_check("model_tool_diagnostic", type(exc).__name__)
    finally:
        run_enablement_rollback(context, state, policy_backup, skill_backup)
        _rollback_check(state, checks)
        if product_before is not None and queue_before:
            invariants = evaluate_readonly_invariants(
                context,
                queue_before,
                product_before,
            )
            record_readonly_invariants(state, checks, invariants)
            if not invariants.ok:
                state.result = "MODEL_TOOL_DIAGNOSTIC_FAILED"
                state.failure_code = "final_invariant_failed"
                state.next_action = "RESTORE_TOOLS_DENIED_BASELINE"
        try:
            evidence_log, evidence_json = _publish(
                context,
                contract,
                state,
                checks,
                stamp,
            )
        except Exception as exc:
            state.result = "MODEL_TOOL_DIAGNOSTIC_EVIDENCE_PUBLISH_FAILED"
            state.failure_code = type(exc).__name__
            state.next_action = "FIX_EVIDENCE_PUBLICATION_WITHOUT_RUNTIME_RETRY"
            state.evidence_commit = ""
            state.evidence_remote_verified = False
    return evidence_log, evidence_json
