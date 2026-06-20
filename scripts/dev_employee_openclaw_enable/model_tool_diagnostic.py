from __future__ import annotations

import tempfile
from dataclasses import replace
from pathlib import Path
from typing import Any

from .activation_transaction import activate_validated_candidate
from .agent_acceptance import run_automatic_acceptance
from .agent_skill_policy import resolve_default_agent_id
from .effective_surface_inventory import probe_approved_effective_tool_surface
from .enablement_rollback import run_enablement_rollback
from .evidence import publish_evidence
from .model_tool_diagnostic_contract import ModelToolDiagnosticContract
from .models import CheckRecorder, RepoSnapshot, RunState, RuntimeContext
from .plugin_runtime import verify_plugin_runtime
from .policy import PolicyBackup
from .preflight_checks import run_transaction_preflight
from .readonly_invariants import evaluate_readonly_invariants, record_readonly_invariants
from .skill_installation import SkillBackup
from .state import load_json


PASS_RESULT = "MODEL_TOOL_CALL_AND_ORIS_ROUTING_PASS"
CAPABILITY_RESULT = "MODEL_TOOL_CALL_CAPABILITY_NOT_DEMONSTRATED"
ROUTING_RESULT = "ORIS_AGENT_HARNESS_ROUTING_FAILED"
INCONSISTENT_RESULT = "MODEL_TOOL_DIAGNOSTIC_INCONSISTENT"


def _diagnostic_context(
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


def _classify(
    state: RunState,
    checks: CheckRecorder,
    automatic: dict[str, Any],
    control_tool: str,
    oris_tool: str,
) -> None:
    telemetry = automatic.get("telemetry")
    telemetry = telemetry if isinstance(telemetry, dict) else {}
    seen = {
        name
        for name in telemetry.get("expected_tools_seen", [])
        if isinstance(name, str)
    }
    control_called = control_tool in seen
    oris_called = oris_tool in seen
    privacy_ok = bool(
        telemetry.get("schema_ok")
        and telemetry.get("content_safe")
        and telemetry.get("parent_permissions_ok")
        and telemetry.get("file_permissions_ok")
        and telemetry.get("only_approved_tools_used")
    )
    state.telemetry_privacy_pass = privacy_ok
    state.native_agent_acceptance_pass = control_called and oris_called
    state.details["model_tool_diagnostic"] = {
        "control_tool_called": control_called,
        "oris_tool_called": oris_called,
        "provider_runtime_facts": telemetry.get("providers_seen", []),
        "model_runtime_facts": telemetry.get("models_seen", []),
        "persisted_session": bool(telemetry.get("persisted_session")),
        "gateway_transport_proven": bool(automatic.get("gateway_transport_proven")),
        "telemetry_privacy_pass": privacy_ok,
        "conversation_content_recorded": False,
        "tool_arguments_or_results_recorded": False,
        "session_identifier_recorded": False,
    }
    if not privacy_ok:
        state.result = "MODEL_TOOL_DIAGNOSTIC_PRIVACY_FAILED"
        state.failure_code = "telemetry_privacy_failed"
        state.next_action = "FIX_TELEMETRY_PRIVACY_BEFORE_RETRY"
        checks.fail_check("model_tool_diagnostic_privacy", state.failure_code)
    elif control_called and oris_called:
        state.result = PASS_RESULT
        state.failure_code = ""
        state.next_action = "RUN_THREE_TOOL_NATIVE_LANGUAGE_ACCEPTANCE"
        checks.pass_check(
            "model_tool_call_capability",
            "safe built-in control tool was called through the native Agent",
        )
        checks.pass_check(
            "oris_agent_harness_routing",
            "ORIS queue status tool was called through the native Agent",
        )
    elif control_called:
        state.result = ROUTING_RESULT
        state.failure_code = "oris_tool_not_called"
        state.next_action = "FIX_ORIS_AGENT_HARNESS_ROUTING"
        checks.pass_check(
            "model_tool_call_capability",
            "safe built-in control tool was called through the native Agent",
        )
        checks.fail_check("oris_agent_harness_routing", state.failure_code)
    elif oris_called:
        state.result = INCONSISTENT_RESULT
        state.failure_code = "oris_called_without_control_tool"
        state.next_action = "FIX_CONTROL_TOOL_SELECTION_OR_TELEMETRY_CORRELATION"
        checks.fail_check("model_tool_call_capability", state.failure_code)
        checks.pass_check(
            "oris_agent_harness_routing",
            "ORIS queue status tool was called through the native Agent",
        )
    else:
        state.result = CAPABILITY_RESULT
        state.failure_code = "no_tool_call_observed"
        state.next_action = "DIAGNOSE_PROVIDER_MODEL_OR_GENERIC_AGENT_HARNESS"
        checks.fail_check("model_tool_call_capability", state.failure_code)
        checks.not_checked(
            "oris_agent_harness_routing",
            "generic tool-call capability was not demonstrated",
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

        runtime = verify_plugin_runtime(context)
        state.write_tools_absent = not bool(runtime.get("write_tools"))
        if not runtime.get("ok") or not state.write_tools_absent:
            raise RuntimeError("plugin runtime contract failed")
        checks.pass_check(
            "model_tool_plugin_runtime",
            "read-only Plugin tools and hooks verified",
        )

        config = load_json(context.openclaw_config)
        agent_id = resolve_default_agent_id(config)
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

        diagnostic_context = _diagnostic_context(context, contract, control_tool)
        automatic = run_automatic_acceptance(diagnostic_context, stamp)
        state.details["native_agent_acceptance"] = automatic
        _classify(
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
        if state.rollback_healthy == "YES":
            checks.pass_check(
                "model_tool_diagnostic_rollback",
                "exact tools-denied baseline and healthy Gateway restored",
            )
        else:
            checks.fail_check(
                "model_tool_diagnostic_rollback",
                "rollback did not restore the healthy tools-denied baseline",
            )
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
            evidence_log, evidence_json = publish_evidence(
                context,
                state,
                checks,
                stamp,
                Path(tempfile.mkdtemp(prefix=f"oris-model-tool-{stamp}-")),
                contract.evidence,
            )
        except Exception as exc:
            state.result = "MODEL_TOOL_DIAGNOSTIC_EVIDENCE_PUBLISH_FAILED"
            state.failure_code = type(exc).__name__
            state.next_action = "FIX_EVIDENCE_PUBLICATION_WITHOUT_RUNTIME_RETRY"
            state.evidence_commit = ""
            state.evidence_remote_verified = False
    return evidence_log, evidence_json
