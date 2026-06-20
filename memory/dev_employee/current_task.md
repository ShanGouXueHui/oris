# Current AI Dev Employee Task

Status: `handoff_archived_pending_new_chat_code_first_continuation`

Task id: `commercial-openclaw-readonly-tool-enable-20260618`

Current step: `new_chat_audit_current_main_then_diagnose_effective_tool_surface`

## Objective

First prove that current `main` has no duplicate definitions, competing authorities, import cycles, forbidden hardcoding, oversized mixed-responsibility modules, stale execution paths or configuration-contract errors.

Only after that code gate passes, determine whether these three approved ORIS tools are present in the selected Agent session's model-facing OpenClaw tool inventory:

- `oris_queue_status`;
- `oris_task_status`;
- `oris_latest_task_status`.

A third natural-language enablement attempt remains prohibited until this boundary is resolved.

## Durable handoff

The long 2026-06-20 conversation has been archived in GitHub:

- session archive: `memory/dev_employee/SESSION_ARCHIVE_2026-06-20.md`;
- environment and working context: `memory/dev_employee/ENVIRONMENT_AND_WORKING_CONTEXT_2026-06-20.md`;
- next-chat prompt: `memory/dev_employee/NEXT_CHAT_HANDOFF_2026-06-20.md`;
- code-first gate: `docs/DEV_EMPLOYEE_CODE_FIRST_CONTINUATION_GATE_2026-06-20.md`.

The archive includes the original continuation mandate, irreversible architecture decisions, environment, repositories, database boundary, Provider/Model rules, interaction preferences, engineering standards, execution history, failures, remediations, unfinished work and commercial roadmap.

## Latest controlled activation evidence

Evidence commit:

`d5cea6980ad46a51cb4f26f8e6229c11539ea2d5`

Passed before failure:

- source governance and named automatic selftests;
- private single-scope candidate native dry-run;
- exact validated-config-to-backup hash equality;
- managed routing Skill installation and visibility to Agent `main`;
- single-scope policy activation;
- existing Gateway restart and health;
- exact plugin read-only tool and typed-hook inventory;
- all three direct ORIS read-only calls;
- queue invariance after direct calls.

Three native Agent turns completed through Gateway in one persisted session:

- all return codes were zero;
- all outputs were structured and present;
- no embedded fallback occurred;
- `model_call_ended=3`;
- `agent_end=3`.

However:

- `after_tool_call=0`;
- no approved tool name was reported;
- no approved tool appeared in telemetry;
- native Agent acceptance failed.

Rollback restored the exact tools-denied config, marker and routing Skill state and left Gateway healthy. No task, product mutation or write tool occurred.

## Unresolved boundary

Direct `/tools/invoke` success proves plugin endpoints. Plugin inventory proves registration. Skill visibility proves instruction visibility.

None proves that the selected Agent session and runtime model received the tools in its effective model-facing inventory.

Two explanations remain:

1. the optional ORIS tools were absent from the effective inventory;
2. the tools were present, but the runtime provider/model did not issue tool calls.

## Code-first continuation requirement

Before any runtime diagnostic:

1. inspect the entire current target package and wrappers;
2. remove duplicate function, class and variable definitions;
3. remove duplicate parsers, policies, validators, service helpers, rollback helpers, evidence publishers and entrypoints;
4. enforce one authority per rule;
5. fix import cycles, hardcoding, oversized modules, legacy paths and contract errors;
6. separate configuration from code;
7. obtain `CODE_AUDIT_PASS` on the exact current `main` commit.

No OpenClaw access, Gateway restart, `tools.effective`, model turn or task submission is allowed before the code gate passes.

## Prepared effective-tool-surface diagnostic

Authoritative plan:

`docs/DEV_EMPLOYEE_EFFECTIVE_TOOL_SURFACE_DIAGNOSTIC_PLAN_2026-06-20.md`

Entrypoint:

`scripts/dev_employee_diagnose_openclaw_effective_tool_surface.sh`

After the code gate passes, run this diagnostic once. It must use native `tools.effective`, run no model turn, invoke no ORIS tool, retain only sanitized approved-tool inventory metadata, always restore the exact tools-denied baseline and publish detached-worktree evidence.

## Next required action

Start a new conversation using:

`memory/dev_employee/NEXT_CHAT_HANDOFF_2026-06-20.md`

In the new conversation:

1. read the mandatory GitHub context;
2. complete and verify the code-first audit;
3. fix all code findings;
4. only then run the effective-tool-surface diagnostic once;
5. read GitHub evidence and choose the materialization or provider/model-capability remediation path.

Do not run `scripts/dev_employee_enable_openclaw_readonly_tools.sh`.

## Unfinished commercialization work

- native natural-language acceptance for all three read-only tools;
- approved-only non-zero `after_tool_call` telemetry;
- real privacy-safe model/tool/agent latency baseline;
- read-only P0 completion persistence;
- typed write actions with approval, RBAC, project authorization, idempotency and audit;
- generic project onboarding and capability discovery;
- Admin UI Provider/Model/Policy management;
- monitoring, privacy/retention, backup/restore and disaster recovery;
- multi-tenant identity, quota, metering and commercial packaging;
- production validation.

## Commercial sequence

1. code-first audit and correction on current `main`;
2. resolve effective tool materialization versus provider/model capability;
3. complete native read-only tool and telemetry acceptance;
4. establish privacy-safe real latency baselines;
5. design typed write actions only after P0 passes;
6. generic onboarding and capability discovery;
7. controlled Admin management;
8. operations, privacy, backup and DR;
9. multi-tenant commercial packaging.
