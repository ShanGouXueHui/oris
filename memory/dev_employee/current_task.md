# Current AI Dev Employee Task

Status: `three_tool_native_acceptance_passed_support_tool_contract_fix_pending`

Task id: `commercial-openclaw-readonly-tool-enable-20260618`

Current step: `merge_bounded_native_skill_support_contract_then_rerun_once`

## Latest complete acceptance evidence

Evidence commit:

`59725fd783732464b6aec0f249868e78e30a5da2`

Reported result:

`FAILED / RuntimeError`

The previous telemetry schema correction worked:

- `schema_ok=true`;
- `execution_outcome_ok=true`;
- all three ORIS tools were called successfully exactly once;
- no failed model, tool, or Agent outcome was recorded.

The complete runtime path also proved:

- source governance and automatic selftests passed;
- Free Mesh protocol version 2 passed;
- all direct probes passed;
- three native Agent turns completed through Gateway;
- one persisted native session and the exact three-turn boundary passed;
- telemetry content safety and file permissions passed;
- queue and product baselines remained protected;
- rollback restored the exact tools-denied configuration;
- no product task or write tool was introduced.

Observed telemetry counts:

- `model_call_ended=7`;
- `agent_end=3`;
- `after_tool_call=4`;
- `oris_queue_status=1`;
- `oris_latest_task_status=1`;
- `oris_task_status=1`;
- native core tool `read=1`.

## Accurate failure boundary

The only rejection was:

`unexpected_tools_seen=[read]`

OpenClaw injects a compact Skill catalog rather than every complete Skill body. A model may therefore use the native `read` tool to load the selected `SKILL.md` body before applying it.

The previous validator incorrectly treated the native Skill-hydration call as an additional ORIS business capability.

## Correct authority separation

### ORIS business tools

The approved ORIS capability set remains unchanged:

- `oris_queue_status`;
- `oris_task_status`;
- `oris_latest_task_status`.

All three must remain Plugin-owned and must each complete successfully.

### Native support tool

The acceptance contract separately declares:

- tool: `read`;
- maximum calls: `1`;
- purpose: load the approved routing Skill body from the native OpenClaw Skill catalog.

This does not add `read` to the ORIS approved-tool set and does not modify the active OpenClaw tool surface.

## Mandatory rejection rules

The run still fails when:

- a support tool exceeds its configured count;
- a support-tool call reports failure;
- a support tool appears after the first ORIS business-tool call;
- any undeclared tool appears;
- a support tool overlaps an ORIS business tool;
- a known write-capable tool is configured as support;
- any ORIS tool lacks a successful call;
- any Agent completion fails;
- schema, privacy, permissions, session, turn, queue, product, route, listener, or source invariants fail.

No tool arguments, results, conversation content, Skill body, or filesystem path may be recorded in GitHub evidence.

## Current runtime state

The failed transaction rolled back successfully:

- exact tools-denied configuration restored;
- previous marker and routing Skill restored;
- Gateway healthy;
- queue and product unchanged;
- write tools absent.

## Next required action

1. merge the bounded native Skill support-tool contract only after the exact branch passes the unified code-first audit;
2. rerun the existing complete acceptance exactly once:

`scripts/dev_employee_enable_openclaw_readonly_tools.sh`

Success requires all three ORIS tools plus zero or one successful pre-ORIS Skill-hydration `read`, with every existing final invariant passing.

## Prohibitions

- no write tools or typed write actions in this task;
- no product task submission;
- no OpenClaw reinstall or upgrade;
- no provider/model hardcoding;
- no public exposure of ports `18891` or `18892`;
- do not touch production host `8.136.28.6`.
