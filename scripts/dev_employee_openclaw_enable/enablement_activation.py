from __future__ import annotations

from .gateway_http import direct_readonly_probe, verify_public_routes
from .models import CheckRecorder, RunState, RuntimeContext
from .plugin_runtime import verify_plugin_runtime
from .policy import PolicyApplication, PolicyBackup, apply_readonly_policy
from .service_control import GatewayServiceError, restart_service_and_wait
from .skill_installation import SkillBackup, install_routing_skill
from .skill_runtime import verify_routing_skill_runtime
from .state import active_queue_count, queue_fingerprint


def activate_candidate(
    context: RuntimeContext,
    state: RunState,
    checks: CheckRecorder,
    policy_backup: PolicyBackup,
    skill_backup: SkillBackup,
) -> PolicyApplication:
    state.mutation_started = True
    skill_details = install_routing_skill(context, skill_backup)
    state.routing_skill_installed = True
    state.details["routing_skill"] = skill_details
    checks.pass_check(
        "routing_skill",
        "managed ORIS read-only routing skill installed",
    )

    application = apply_readonly_policy(context, policy_backup)
    state.selected_policy_mode = application.mode
    state.details["policy_application"] = application.evidence()
    state.config_scope_valid = True
    try:
        state.details["candidate_gateway_restart"] = restart_service_and_wait(context)
    except GatewayServiceError as exc:
        state.details["gateway_failure_diagnostics"] = exc.safe_evidence
        checks.fail_check("candidate_gateway_health", exc.code)
        raise
    checks.pass_check(
        "controlled_policy_enablement",
        "minimal approved tool and agent-skill policy applied",
    )

    skill_runtime = verify_routing_skill_runtime(
        context,
        application.skill_policy.agent_id,
    )
    state.details["routing_skill_runtime"] = skill_runtime
    if not skill_runtime.get("visible"):
        raise RuntimeError("routing skill is not visible to the selected agent")
    checks.pass_check(
        "routing_skill_runtime",
        "routing skill is eligible and visible to the selected agent",
    )
    return application


def verify_runtime_and_direct_calls(
    context: RuntimeContext,
    state: RunState,
    checks: CheckRecorder,
    baseline_tool: str,
    queue_before: str,
) -> None:
    if not verify_public_routes(context)["ok"]:
        raise RuntimeError("public routes failed after Gateway restart")
    runtime = verify_plugin_runtime(context)
    if not runtime.get("ok"):
        raise RuntimeError("plugin runtime contract failed after enablement")
    state.write_tools_absent = not runtime.get("write_tools")
    checks.pass_check(
        "plugin_runtime",
        "exact read-only tools and typed hooks verified",
    )

    direct = direct_readonly_probe(context, baseline_tool)
    state.details["direct_invocation"] = direct
    if not direct["ok"]:
        state.direct_tool_calls_pass = False
        raise RuntimeError("direct approved read-only tool invocation failed")
    state.direct_tool_calls_pass = True
    checks.pass_check(
        "direct_tool_calls",
        "three ORIS tools and safe baseline tool passed",
    )

    if (
        queue_fingerprint(context.repo_root) != queue_before
        or active_queue_count(context.repo_root) != 0
    ):
        state.queue_unchanged = False
        raise RuntimeError("queue changed during direct read-only tool calls")
    checks.pass_check("queue_after_direct_calls", "queue fingerprint is unchanged")
