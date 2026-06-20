# Dev Employee Native Skill Support Tool Contract — 2026-06-20

## Evidence boundary

The second complete native read-only acceptance is recorded in sanitized evidence commit:

`59725fd783732464b6aec0f249868e78e30a5da2`

That run proved the three ORIS business tools, schema and execution outcomes, but rejected one native `read` call used to load the approved Routing Skill body.

The corrected contract was merged in:

`bf084296d60de6941303f227cde8f952a6117147`

The final accepted native read-only run is recorded in:

`65217d4bb81f4ac3cd8c6d917af95425d2b47529`

Final result:

`ENABLED_READONLY_AUTOMATIC_ACCEPTED`

The final run proved:

- source governance, selftests, readiness, Gateway, routes, listeners, queue, product and ORIS source baselines passed;
- Free Mesh protocol version 2 and tool calling passed;
- all three Plugin-owned ORIS tools passed direct invocation;
- all three native natural-language turns passed through Gateway;
- one persisted native session and the exact three-turn boundary passed;
- schema, execution outcomes, privacy and permissions passed;
- the bounded native `read` support call passed;
- no undeclared tool was observed;
- no product task or write tool was introduced;
- the validated read-only policy and Routing Skill were retained;
- rollback was not required.

## Native Skill loading fact

OpenClaw injects a compact Skill catalog into the Agent system prompt rather than embedding every complete `SKILL.md` body. The catalog includes Skill identity, description and location. A model may therefore use the native `read` tool to load the selected Skill body before applying it.

Official reference:

`https://docs.openclaw.ai/tools/skills`

The ORIS Routing Skill remains authoritative and explicitly requires the three typed ORIS tools while forbidding filesystem access as a fallback for live ORIS status.

## Correct authority separation

The previous acceptance rule incorrectly treated every non-ORIS tool as an unauthorized business capability. The corrected contract has two separate domains.

### ORIS business tools

These remain the only approved ORIS business capabilities:

- `oris_queue_status`;
- `oris_task_status`;
- `oris_latest_task_status`.

All three must be Plugin-owned, present in the effective surface, called successfully and correlated to the persisted native session.

### Native support tool

A native support tool is not an ORIS business tool. It may be used only to support the native OpenClaw Agent/Skill lifecycle.

The current contract permits:

- tool: `read`;
- maximum calls: `1`;
- purpose: load the approved Routing Skill body from the native Skill catalog entry;
- timing: before the first ORIS business-tool call;
- outcome: successful only.

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
- schema, privacy, permissions, session correlation or exact-turn checks fail.

No tool arguments, tool results, conversation content, Skill body or filesystem path is recorded in GitHub evidence.

## Non-expansion statement

This contract does not:

- add `read` to the ORIS approved-tool set;
- add a new tool to the OpenClaw effective surface;
- broaden the active OpenClaw profile;
- modify the Plugin business capability surface;
- reinstall or upgrade OpenClaw;
- change provider or model selection;
- authorize write tools or product-task submission.

It preserves strict rejection of every undeclared tool.

## Current status

This contract is implemented, tested and accepted in the retained read-only runtime.

Do not rerun the read-only enablement merely to reconfirm this contract.

Future changes to Skill-loading behavior, OpenClaw version or support-tool authority require:

1. a fresh code-first audit;
2. a versioned contract/config change;
3. regression tests;
4. a separate controlled runtime validation with exact rollback.
