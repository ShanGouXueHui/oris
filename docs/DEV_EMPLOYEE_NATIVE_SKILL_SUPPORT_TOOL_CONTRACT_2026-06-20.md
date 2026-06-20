# Dev Employee Native Skill Support Tool Contract — 2026-06-20

## Evidence boundary

The second complete native read-only acceptance is recorded in sanitized evidence commit:

`59725fd783732464b6aec0f249868e78e30a5da2`

The run proved:

- source governance, selftests, readiness, Gateway, routes, listeners, queue, product, and ORIS source baselines passed;
- Free Mesh protocol version 2 and tool calling passed;
- all three Plugin-owned ORIS tools passed direct invocation;
- all three native natural-language turns returned successfully through Gateway;
- one persisted native session and the exact three-turn boundary passed;
- `schema_ok=true`;
- `execution_outcome_ok=true`;
- each required ORIS tool was called successfully exactly once;
- telemetry content safety and file permissions passed;
- no product task or write tool was introduced;
- exact tools-denied rollback completed successfully.

The sole rejection was one additional native core-tool call named `read`.

## Native Skill loading fact

OpenClaw injects a compact Skill catalog into the Agent system prompt rather than embedding every complete `SKILL.md` body. The catalog includes Skill identity, description, and location. A model may therefore use the native read tool to load the selected Skill body before applying it.

Official reference:

`https://docs.openclaw.ai/tools/skills`

The ORIS routing Skill remains authoritative and explicitly requires the three typed ORIS tools while forbidding filesystem access as a fallback for live ORIS status.

## Correct authority separation

The previous acceptance rule incorrectly treated every non-ORIS tool as an unauthorized business capability. The corrected contract has two separate domains.

### ORIS business tools

These remain the only approved ORIS business capabilities:

- `oris_queue_status`;
- `oris_task_status`;
- `oris_latest_task_status`.

All three must be Plugin-owned, present in the effective surface, called successfully, and correlated to the persisted native session.

### Native support tools

A native support tool is not an ORIS business tool. It may be used only to support the native OpenClaw Agent/Skill lifecycle.

The current contract permits:

- tool: `read`;
- maximum calls: `1`;
- purpose: load the approved routing Skill body from the native Skill catalog entry.

This declaration is stored in `config/dev_employee/openclaw_readonly_acceptance.json`, not embedded in telemetry logic.

## Mandatory restrictions

A native support-tool declaration is rejected when:

- it overlaps an approved ORIS business tool;
- it is a known write-capable core tool;
- its maximum call count is outside the configured Agent-turn boundary;
- its name is duplicated;
- its purpose is absent.

Runtime acceptance is rejected when:

- a support tool exceeds its call limit;
- a support-tool call reports failure;
- a support tool appears after the first ORIS business-tool call;
- any undeclared tool appears;
- any required ORIS tool lacks a successful call;
- any Agent completion reports failure;
- schema, privacy, permissions, session correlation, or exact-turn checks fail.

No tool arguments, tool results, conversation content, Skill body, or filesystem path is recorded in GitHub evidence.

## Non-expansion statement

This correction does not:

- add `read` to the ORIS approved-tool set;
- add a new tool to the OpenClaw effective surface;
- broaden the active OpenClaw profile;
- modify the Plugin;
- reinstall or upgrade OpenClaw;
- change provider or model selection;
- authorize write tools or product-task submission.

It corrects the acceptance interpretation of a pre-existing native read-only support call while preserving strict rejection of every other undeclared tool.

## Next controlled action

After the exact source revision passes the unified code-first audit, run the complete read-only acceptance once through:

`scripts/dev_employee_enable_openclaw_readonly_tools.sh`

Success requires the three ORIS tools plus zero or one successful pre-ORIS native Skill hydration call, with every existing final invariant still passing.
