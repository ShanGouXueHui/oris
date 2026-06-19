from __future__ import annotations

import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .agent_acceptance import run_automatic_acceptance
from .context import load_context
from .evidence import write_and_commit_evidence
from .gateway import (
    direct_readonly_probe,
    gateway_pid,
    restart_gateway,
    select_safe_baseline_tool,
    verify_plugin_runtime,
    verify_public_routes,
)
from .models import CheckRecorder, RunState, RuntimeContext
from .policy import (
    PolicyBackup,
    apply_readonly_policy,
    create_backup,
    finalize_marker,
    restore_denied_policy,
    validate_config_scope,
    validate_denied_baseline,
)
from .process import run
from .state import (
    active_queue_count,
    listener_is_loopback_only,
    load_json,
    queue_fingerprint,
    repository_is_clean,
    repository_snapshot,
    repository_unchanged,
)


REQUIRED_COMMANDS = ("git", "openclaw", "systemctl", "ss")


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


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


def _summary(
    context: RuntimeContext | None,
    state: RunState,
    checks: CheckRecorder,
    evidence_log: str,
    evidence_json: str,
) -> None:
    print("===== SUMMARY =====")
    print(f"RESULT={state.result}")
    print(f"TASK_ID={context.task_id if context else ''}")
    print(f"FAILURE_CODE={state.failure_code}")
    print(f"SELECTED_POLICY_MODE={state.selected_policy_mode}")
    print(f"CHECKS_TOTAL={len(checks.checks)}")
    print(f"CHECKS_PASS={checks.pass_count}")
    print(f"CHECKS_FAIL={checks.fail_count}")
    print(f"DIRECT_TOOL_CALLS_PASS={'YES' if state.direct_tool_calls_pass else 'NO'}")
    print(f"NATIVE_AGENT_ACCEPTANCE_PASS={'YES' if state.native_agent_acceptance_pass else 'NO'}")
    print(f"TELEMETRY_PRIVACY_PASS={'YES' if state.telemetry_privacy_pass else 'NO'}")
    print(f"CONFIG_SCOPE_VALID={'YES' if state.config_scope_valid else 'NO'}")
    print(f"QUEUE_UNCHANGED={'YES' if state.queue_unchanged else 'NO'}")
    print(f"PRODUCT_UNCHANGED={'YES' if state.product_unchanged else 'NO'}")
    print(f"WRITE_TOOLS_ABSENT={'YES' if state.write_tools_absent else 'NO'}")
    print(f"ROLLBACK_COUNT={state.rollback_count}")
    print(f"ROLLBACK_HEALTHY={state.rollback_healthy}")
    print("PRODUCT_TASK_SUBMITTED=NO")
    print("WRITE_TOOLS_ADDED=NO")
    print("OPENCLAW_REINSTALLED_OR_UPGRADED=NO")
    print(f"EVIDENCE_LOG={evidence_log}")
    print(f"EVIDENCE_JSON={evidence_json}")
    print(f"EVIDENCE_COMMIT={state.evidence_commit}")
    print(f"EVIDENCE_REMOTE_VERIFIED={'YES' if state.evidence_remote_verified else 'NO'}")
    print(f"NEXT_ACTION={state.next_action}")
    print("SEND_TO_CHAT=THIS_SUMMARY_ONLY")
    print("===== END SUMMARY =====")


def _preflight(
    context: RuntimeContext,
    checks: CheckRecorder,
) -> tuple[str, str, object, object, str, int]:
    _require_commands()
    _require_private_file(context.openclaw_config)
    _require_private_file(context.marker_file)
    if not context.product_repo.is_dir():
        raise RuntimeError("baseline product repository is missing")
    readiness = load_json(context.readiness_evidence)
    if readiness.get("result") != "READY":
        raise RuntimeError("authoritative readiness evidence is not READY")
    checks.pass_check("authoritative_readiness", "latest READY evidence verified")

    denied = validate_denied_baseline(context)
    checks.pass_check("tools_denied_baseline", "approved tools remain denied before mutation")
    if not _gateway_active(context):
        raise RuntimeError("existing OpenClaw Gateway is not active")
    routes = verify_public_routes(context)
    if not routes["ok"]:
        raise RuntimeError("public native UI or restricted route contract failed")
    checks.pass_check("gateway_and_routes", "existing Gateway and native public root are healthy")

    if not all(listener_is_loopback_only(port) for port in context.internal_ports):
        raise RuntimeError("an internal ORIS listener is not loopback-only")
    checks.pass_check("private_internal_listeners", "required ORIS listeners are loopback-only")

    queue_before = queue_fingerprint(context.repo_root)
    active_before = active_queue_count(context.repo_root)
    if active_before != 0:
        raise RuntimeError("active ORIS product task exists")
    checks.pass_check("queue_baseline", "zero active tasks and queue fingerprint captured")

    product_before = repository_snapshot(context.product_repo)
    if not (
        product_before.head == context.expected_product_commit
        and product_before.remote_main == context.expected_product_commit
        and repository_is_clean(product_before)
    ):
        raise RuntimeError("product repository baseline differs from authoritative task state")
    checks.pass_check("product_baseline", "product HEAD, remote main, and clean worktree verified")

    oris_before = repository_snapshot(context.repo_root)
    if not repository_is_clean(oris_before):
        raise RuntimeError("ORIS primary worktree is not clean")
    baseline_tool = select_safe_baseline_tool(context)
    checks.pass_check("safe_builtin_baseline", "safe built-in tool is accessible before mutation")
    return queue_before, baseline_tool, product_before, oris_before, gateway_pid(context), active_before


def _run(context: RuntimeContext, state: RunState, checks: CheckRecorder, stamp: str) -> tuple[str, str]:
    backup: PolicyBackup | None = None
    evidence_log = ""
    evidence_json = ""
    queue_before = ""
    product_before = None
    oris_before = None
    try:
        queue_before, baseline_tool, product_before, oris_before, _, _ = _preflight(context, checks)
        backup = create_backup(context, stamp)
        checks.pass_check("private_backup", "tools-denied config and marker backup created")

        state.selected_policy_mode = apply_readonly_policy(context, backup)
        state.mutation_started = True
        state.config_scope_valid = True
        restart_gateway(context)
        checks.pass_check("controlled_policy_enablement", "minimal approved read-only policy applied")

        routes = verify_public_routes(context)
        if not routes["ok"]:
            raise RuntimeError("public routes failed after Gateway restart")
        runtime = verify_plugin_runtime(context)
        if not runtime.get("ok"):
            raise RuntimeError("plugin runtime contract failed after enablement")
        state.write_tools_absent = not runtime.get("write_tools")
        checks.pass_check("plugin_runtime", "exact read-only tools and typed hooks verified")

        direct = direct_readonly_probe(context, baseline_tool)
        state.details["direct_invocation"] = direct
        if not direct["ok"]:
            raise RuntimeError("direct approved read-only tool invocation failed")
        state.direct_tool_calls_pass = True
        checks.pass_check("direct_tool_calls", "three ORIS tools and safe baseline tool passed")

        if queue_fingerprint(context.repo_root) != queue_before or active_queue_count(context.repo_root) != 0:
            raise RuntimeError("queue changed during direct read-only tool calls")
        checks.pass_check("queue_after_direct_calls", "queue fingerprint is unchanged")

        automatic = run_automatic_acceptance(context, stamp)
        state.details["native_agent_acceptance"] = automatic
        if not automatic.get("accepted"):
            raise RuntimeError(str(automatic.get("reason") or "automatic native agent acceptance failed"))
        state.native_agent_acceptance_pass = True
        telemetry = automatic.get("telemetry") or {}
        state.telemetry_privacy_pass = bool(
            telemetry.get("schema_ok") and telemetry.get("content_safe")
        )
        if not state.telemetry_privacy_pass:
            raise RuntimeError("telemetry privacy or schema validation failed")
        checks.pass_check("automatic_native_agent_acceptance", "three natural-language turns completed automatically")
        checks.pass_check("telemetry_privacy", "typed hook telemetry is private and schema-safe")

        if queue_fingerprint(context.repo_root) != queue_before or active_queue_count(context.repo_root) != 0:
            raise RuntimeError("queue changed during native agent acceptance")
        state.queue_unchanged = True
        checks.pass_check("final_queue_invariant", "queue fingerprint and active count are unchanged")

        product_after = repository_snapshot(context.product_repo)
        if not repository_unchanged(product_before, product_after):
            raise RuntimeError("product repository changed during read-only acceptance")
        state.product_unchanged = True
        checks.pass_check("final_product_invariant", "product repository is unchanged")

        validate_config_scope(context, backup, state.selected_policy_mode)
        runtime_final = verify_plugin_runtime(context)
        if not runtime_final.get("ok") or runtime_final.get("write_tools"):
            raise RuntimeError("final plugin runtime contract failed")
        if not all(listener_is_loopback_only(port) for port in context.internal_ports):
            raise RuntimeError("an internal listener exposure changed")
        if not verify_public_routes(context)["ok"]:
            raise RuntimeError("final public route contract failed")
        if not repository_unchanged(oris_before, repository_snapshot(context.repo_root)):
            raise RuntimeError("ORIS primary worktree changed before evidence commit")
        checks.pass_check("final_runtime_and_route_invariants", "runtime, routes, listeners, and worktree verified")

        finalize_marker(context, backup, state.selected_policy_mode, stamp)
        checks.pass_check("private_marker", "automatic read-only acceptance recorded privately")
        state.result = "ENABLED_READONLY_AUTOMATIC_ACCEPTED"
        state.failure_code = ""
        state.next_action = "PERSIST_COMPLETION_AND_BEGIN_P1_TYPED_WRITE_ACTION_DESIGN"
        state.rollback_healthy = "NOT_REQUIRED"
        commit, evidence_log, evidence_json = write_and_commit_evidence(
            context,
            state,
            checks,
            stamp,
            Path(tempfile.gettempdir()) / f"oris-enable-evidence-{stamp}",
        )
        state.evidence_commit = commit
        state.evidence_remote_verified = True
        state.mutation_started = False
        return evidence_log, evidence_json
    except Exception as exc:
        state.failure_code = type(exc).__name__ + ":" + str(exc)
        state.next_action = "FIX_AUTOMATIC_ENABLEMENT_FAILURE_WITH_TOOLS_DENIED"
        checks.fail_check("automatic_enablement", type(exc).__name__)
        if state.mutation_started and backup is not None:
            try:
                restore_denied_policy(context, backup)
                restart_gateway(context)
                state.rollback_count += 1
                state.rollback_healthy = "YES"
                state.mutation_started = False
            except Exception:
                state.rollback_healthy = "NO"
        try:
            temp_root = Path(tempfile.mkdtemp(prefix=f"oris-enable-evidence-{stamp}-"))
            commit, evidence_log, evidence_json = write_and_commit_evidence(
                context, state, checks, stamp, temp_root
            )
            state.evidence_commit = commit
            state.evidence_remote_verified = True
        except Exception:
            pass
        return evidence_log, evidence_json


def main() -> int:
    state = RunState()
    checks = CheckRecorder()
    context: RuntimeContext | None = None
    evidence_log = ""
    evidence_json = ""
    try:
        context = load_context()
        evidence_log, evidence_json = _run(context, state, checks, _stamp())
    except Exception as exc:
        state.failure_code = type(exc).__name__ + ":" + str(exc)
        checks.fail_check("context_or_bootstrap", type(exc).__name__)
    _summary(context, state, checks, evidence_log, evidence_json)
    return 0 if state.result == "ENABLED_READONLY_AUTOMATIC_ACCEPTED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
