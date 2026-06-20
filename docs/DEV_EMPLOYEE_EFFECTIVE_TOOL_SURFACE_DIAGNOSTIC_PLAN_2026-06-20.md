# Effective Tool Surface Diagnostic Plan — 2026-06-20

## Trigger evidence

Controlled activation evidence commit:

`d5cea6980ad46a51cb4f26f8e6229c11539ea2d5`

The transaction proved:

- source governance and automatic selftests passed;
- private candidate native dry-run passed;
- routing Skill was visible to Agent `main`;
- Gateway restart was healthy;
- exact plugin tool and hook inventory passed;
- all three ORIS tools passed direct typed invocation;
- three native Gateway Agent turns completed with structured output in one persisted session;
- `model_call_ended=3` and `agent_end=3`;
- `after_tool_call=0` and no tool name was reported;
- rollback restored the exact tools-denied baseline and healthy Gateway.

## Unresolved boundary

Direct `/tools/invoke` success and plugin runtime inventory do not prove that the selected Agent session and runtime model received the ORIS tools in its effective model-facing tool surface.

Two explanations remain:

1. the three optional plugin tools were absent from the effective Agent tool inventory; or
2. the tools were present, but the selected runtime provider/model did not issue a tool call.

A third full enablement attempt is prohibited until this boundary is resolved.

## Native diagnostic authority

OpenClaw `2026.5.19` exposes the native Gateway RPC method:

`tools.effective`

It resolves tools using the trusted persisted session context, including:

- Agent id;
- session key;
- selected provider and model;
- effective profile and policy;
- plugin tool materialization;
- model compatibility filters.

The diagnostic must use the installed CLI RPC path:

```text
openclaw gateway call tools.effective --params <private-json> --json
```

## Diagnostic transaction

The diagnostic must:

1. compile the package in an isolated temporary cache;
2. pass source governance and named automatic selftests;
3. verify the exact healthy tools-denied baseline;
4. rebuild the private single-scope candidate;
5. pass native config dry-run;
6. create exact private backups;
7. temporarily install the managed routing Skill and activate the validated policy;
8. restart only the existing `openclaw-gateway.service`;
9. verify routing Skill and plugin runtime inventory;
10. call `tools.effective` for the configured persisted Agent session;
11. retain only sanitized inventory metadata;
12. restore the exact tools-denied config, marker and Skill state;
13. prove final Gateway health;
14. publish detached-worktree evidence.

The diagnostic must not:

- run natural-language model turns;
- invoke any ORIS tool;
- submit a product task;
- add a write tool;
- change the product repository;
- expose internal listeners;
- reinstall or upgrade OpenClaw;
- reinstall the plugin;
- touch production host `8.136.28.6`.

## Accepted evidence fields

Evidence may retain:

- result and safe reason code;
- effective profile;
- total tool count;
- plugin tool count;
- count and names of the three approved ORIS tools only;
- whether each approved tool is owned by `oris-dev-employee`;
- whether all approved tools are present;
- command return code and bounded byte counts;
- active-config and rollback invariants.

Evidence must not retain:

- raw RPC output;
- arbitrary tool descriptions;
- non-approved tool names;
- raw session keys or ids;
- provider credentials;
- config content;
- conversation content;
- tool arguments or results.

## Decision rule

### Approved tools absent

Treat as an OpenClaw effective materialization or session-policy defect. Remediate that layer before any model acceptance retry.

### Approved tools present

Treat policy and optional-tool materialization as proven. The remaining blocker is provider/model tool-call capability or behavior. Diagnose runtime model compatibility and Harness routing without hardcoding a provider or model identity.

### RPC unavailable or unsafe

Rollback and stop. Do not substitute catalog inventory, direct tool calls or prompt inference for the native effective inventory.
