from __future__ import annotations

import tempfile
from pathlib import Path

from .clock import utc_compact_stamp
from .code_audit_cli import audit_code_state
from .context import discover_repo_root, load_context
from .evidence import publish_evidence
from .free_mesh_protocol import probe_free_mesh_protocol
from .model_tool_diagnostic_contract import load_model_tool_diagnostic_contract
from .model_tool_diagnostic_result import PASS_RESULT
from .model_tool_diagnostic_runtime import run_model_tool_diagnostic
from .models import CheckRecorder, RunState, RuntimeContext
from .reporting import print_summary


def main() -> int:
    state = RunState()
    checks = CheckRecorder()
    context: RuntimeContext | None = None
    evidence_log = ""
    evidence_json = ""
    repo_root = discover_repo_root()
    stamp = utc_compact_stamp()
    audit, _, contract_error = audit_code_state(repo_root)
    if not audit.get("ok"):
        state.result = "MODEL_TOOL_DIAGNOSTIC_BLOCKED"
        state.failure_code = contract_error or "code_audit_findings"
        state.next_action = "FIX_ALL_CODE_AUDIT_FINDINGS"
        checks.fail_check("code_audit_gate", "blocked before OpenClaw access")
        print_summary(context, state, checks, evidence_log, evidence_json)
        return 2
    checks.pass_check("code_audit_gate", "exact main revision passed")
    try:
        context = load_context()
        contract = load_model_tool_diagnostic_contract(repo_root)
        protocol = probe_free_mesh_protocol(repo_root)
        state.details["free_mesh_protocol"] = protocol
        if protocol.get("status") != "PASS":
            state.result = "MODEL_TOOL_DIAGNOSTIC_FAILED"
            state.failure_code = "free_mesh_protocol_v2_not_ready"
            state.next_action = "READ_FREE_MESH_SERVICE_JOURNAL"
            checks.fail_check(
                "free_mesh_tool_protocol",
                "Free Mesh protocol v2 tool-calling readiness failed",
            )
            evidence_log, evidence_json = publish_evidence(
                context,
                state,
                checks,
                stamp,
                Path(tempfile.mkdtemp(prefix=f"oris-model-tool-{stamp}-")),
                contract.evidence,
            )
        else:
            checks.pass_check(
                "free_mesh_tool_protocol",
                "loopback Free Mesh protocol v2 and tool calling verified",
            )
            evidence_log, evidence_json = run_model_tool_diagnostic(
                context,
                contract,
                state,
                checks,
                stamp,
            )
    except Exception as exc:
        state.result = "MODEL_TOOL_DIAGNOSTIC_BOOTSTRAP_FAILED"
        state.failure_code = type(exc).__name__
        state.next_action = "FIX_MODEL_TOOL_DIAGNOSTIC_BOOTSTRAP"
        checks.fail_check("diagnostic_bootstrap", type(exc).__name__)
    print_summary(context, state, checks, evidence_log, evidence_json)
    return 0 if state.result == PASS_RESULT else 1


if __name__ == "__main__":
    raise SystemExit(main())
