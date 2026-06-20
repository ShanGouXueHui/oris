# ORIS Dev Employee Current State — 2026-06-20

## Current task

Task id: `commercial-openclaw-readonly-tool-enable-20260618`

Status: `three_tool_native_acceptance_passed_support_tool_contract_fix_pending`

Current step: `merge_bounded_native_skill_support_contract_then_rerun_once`

## Fixed commercial architecture

```text
user
  -> native OpenClaw UI and native sessions
  -> native ORIS Plugin / Agent Harness
  -> ORIS task governance and evidence
  -> Codex real code execution
  -> product commit, tests and ORIS evidence returned through OpenClaw
```

Native OpenClaw remains the commercial primary UI. The custom ORIS Web Console remains restricted diagnostics and rollback only.

Do not reinstall or upgrade OpenClaw. Do not reinstall the Plugin. Do not expose internal listeners. Do not add write tools in this task. Do not touch production host `8.136.28.6`.

## Installed baseline

- Plugin: `oris-dev-employee` `0.1.0`;
- approved ORIS read-only tools: `oris_queue_status`, `oris_task_status`, `oris_latest_task_status`;
- typed hooks: `model_call_ended`, `after_tool_call`, `agent_end`;
- readiness: `26/26 PASS`;
- active product task: none;
- product baseline: `bcb93e17ea88704548101f5e4a5c460e15a80ec7`;
- write tools: absent and unauthorized.

## Resolved boundaries

Evidence `c415c614ac726906186da1756e3beb7c2de003b2` proved effective-tool materialization, model tool-call capability, ORIS Agent Harness routing, persisted-session correlation, privacy-safe telemetry, and healthy exact rollback.

Evidence `22ee300081e98d8e2df4c3f4a495c9608db98d2b` exposed a telemetry schema/outcome conflation. Commit `e3f9ef451f35fee679c4c040d83dcbe017cec9aa` separated those authorities.

## Latest complete acceptance

Evidence commit:

`59725fd783732464b6aec0f249868e78e30a5da2`

Reported result:

`FAILED / RuntimeError`

The previous schema correction is verified by this run:

- `schema_ok=true`;
- `execution_outcome_ok=true`;
- no failed model, tool, or Agent event;
- all three required ORIS tools succeeded exactly once.

The run also proved:

- source governance and automatic selftests passed;
- exact tools-denied baseline and authoritative readiness passed;
- Gateway, routes, and loopback listeners passed;
- queue, product, and ORIS source baselines passed;
- Free Mesh protocol version 2 passed;
- activation candidate, policy, routing Skill, and Plugin runtime passed;
- all direct probes passed;
- three native Agent turns completed through Gateway;
- one persisted native session and exact three-turn boundary passed;
- telemetry content safety and file permissions passed.

Observed telemetry:

- `model_call_ended=7`;
- `agent_end=3`;
- `after_tool_call=4`;
- `oris_queue_status=1`;
- `oris_latest_task_status=1`;
- `oris_task_status=1`;
- native core tool `read=1`.

The only rejection was:

`unexpected_tools_seen=[read]`

Rollback succeeded and restored the exact tools-denied configuration, previous marker, and routing Skill. Gateway remained healthy. No product task or write tool was introduced.

## Accurate root cause

OpenClaw supplies a compact Skill catalog to the Agent instead of embedding every complete `SKILL.md` body. A model may use the native `read` tool to load the selected Skill body before applying it.

The previous acceptance validator used one set for two different authorities:

1. Plugin-owned ORIS business tools;
2. native OpenClaw support tools used by the Agent/Skill lifecycle.

The one native `read` call was therefore incorrectly treated as a fourth ORIS business capability.

## Corrected authority model

### ORIS business authority

The only approved ORIS business tools remain:

- `oris_queue_status`;
- `oris_task_status`;
- `oris_latest_task_status`.

All three must remain Plugin-owned, present, correlated, and successful.

### Native Skill support authority

The acceptance contract separately declares:

- native support tool: `read`;
- maximum calls: `1`;
- purpose: load the approved routing Skill body from the native Skill catalog;
- timing: before the first ORIS business-tool call.

This declaration does not add `read` to the ORIS approved-tool set, does not add a new effective tool, and does not broaden the active OpenClaw profile.

## Enforced rejection rules

Acceptance fails when:

- a support-tool declaration overlaps an ORIS business tool;
- a known write-capable tool is declared as support;
- a support-tool name is duplicated or has no purpose;
- its call limit is invalid;
- a support tool exceeds its call limit;
- a support-tool call fails;
- a support tool occurs after the first ORIS business-tool call;
- any undeclared tool appears;
- any required ORIS tool lacks a successful call;
- any Agent completion fails;
- any schema, privacy, permissions, session, turn, queue, product, route, listener, or source invariant fails.

Tool arguments, results, Skill content, conversation content, and filesystem paths remain excluded from evidence.

## Current runtime state

After rollback:

- exact tools-denied configuration active;
- previous marker and Skill state restored;
- Gateway and Free Mesh healthy;
- queue and product unchanged;
- internal listeners loopback-only;
- write tools absent.

## Next action

After the exact support-tool contract revision passes the unified code-first audit and is merged, run once:

`scripts/dev_employee_enable_openclaw_readonly_tools.sh`

Success requires all three ORIS tools plus zero or one successful pre-ORIS Skill-hydration `read`, with all final invariants passing.

On success:

- retain the validated read-only policy, routing Skill, and private marker;
- persist read-only P0 completion;
- establish the privacy-safe model/tool/Agent latency baseline.

On failure:

- restore the exact tools-denied baseline;
- publish sanitized evidence;
- do not rerun before evidence review.

## Commercial sequence

1. complete and persist native read-only P0;
2. establish privacy-safe real latency baselines;
3. design typed write actions with approval, RBAC, project authorization, idempotency, and audit;
4. generic onboarding and capability discovery;
5. controlled Admin management;
6. monitoring, privacy, backup, and DR;
7. multi-tenant commercial packaging.
