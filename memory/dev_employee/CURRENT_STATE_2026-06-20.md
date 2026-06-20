# ORIS Dev Employee Current State — 2026-06-20

## Current task

Task id:

`commercial-openclaw-readonly-tool-enable-20260618`

Status:

`handoff_archived_pending_new_chat_code_first_continuation`

Current step:

`new_chat_audit_current_main_then_diagnose_effective_tool_surface`

## Fixed commercial architecture

```text
user
  -> native OpenClaw UI and native sessions
  -> native ORIS plugin / Agent Harness
  -> ORIS task governance and evidence
  -> Codex real code execution
  -> product commit, tests and ORIS evidence returned through OpenClaw
```

Native OpenClaw remains the commercial primary UI. The custom ORIS Web Console remains restricted diagnostics and rollback only.

Do not reinstall or upgrade OpenClaw. Do not reinstall the plugin. Do not expose internal listeners. Do not add write tools in this task. Do not touch production host `8.136.28.6`.

## Durable handoff completed

The complete 2026-06-20 conversation state is now persisted in GitHub:

- `memory/dev_employee/SESSION_ARCHIVE_2026-06-20.md`;
- `memory/dev_employee/ENVIRONMENT_AND_WORKING_CONTEXT_2026-06-20.md`;
- `memory/dev_employee/NEXT_CHAT_HANDOFF_2026-06-20.md`;
- `docs/DEV_EMPLOYEE_CODE_FIRST_CONTINUATION_GATE_2026-06-20.md`.

These files preserve the original startup mandate, architecture, environment, systems, database boundary, Provider/Model rules, interaction preferences, engineering standards, execution history, latest failure, rollback state, unfinished work and next decision tree.

## Installed baseline

- plugin: `oris-dev-employee` `0.1.0`;
- installation result: `INSTALLED_TOOLS_DENIED`;
- runtime tools: `oris_queue_status`, `oris_task_status`, `oris_latest_task_status`;
- runtime hooks: `model_call_ended`, `after_tool_call`, `agent_end`;
- readiness: `26/26 PASS`;
- active product task: none;
- current runtime after rollback: exact healthy tools-denied baseline;
- write tools: absent and unauthorized.

## Latest controlled activation

Evidence commit:

`d5cea6980ad46a51cb4f26f8e6229c11539ea2d5`

Result:

`FAILED / RuntimeError`

Passed before failure:

- source governance and named automatic selftests;
- private single-scope candidate native dry-run;
- validated configuration and private backup hash equality;
- routing Skill installation and visibility to Agent `main`;
- single-scope policy activation;
- existing Gateway restart and health;
- exact plugin read-only tool and typed-hook inventory;
- direct invocation of all three approved ORIS tools;
- queue invariance after direct calls.

Three native Agent turns completed through Gateway in one persisted session. Each turn returned zero, produced structured output and avoided embedded fallback.

Observed telemetry:

- `model_call_ended=3`;
- `agent_end=3`;
- `after_tool_call=0`;
- approved tools seen: none;
- unexpected tools seen: none.

Native Agent acceptance failed because no tool invocation occurred.

Rollback completed successfully:

- exact tools-denied config restored;
- routing Skill state restored;
- Gateway restarted and remained healthy;
- rollback failure codes: none;
- no product task, product mutation or write tool occurred.

## Current unresolved boundary

Direct typed invocation proves the plugin endpoint works. Plugin inventory proves registration. Skill visibility proves the instructions are visible.

These facts do not prove the three optional plugin tools were present in the selected Agent session's effective model-facing tool inventory.

Two explanations remain:

1. the approved tools were absent from the effective inventory;
2. the approved tools were present, but the runtime provider/model did not issue tool calls.

A third full enablement attempt is prohibited until this distinction is proven.

## Code-first continuation gate

Authoritative rule:

`docs/DEV_EMPLOYEE_CODE_FIRST_CONTINUATION_GATE_2026-06-20.md`

The next conversation must first audit current `main`, including all newly added effective-surface diagnostic files and wrappers.

Before runtime work, the audit must prove:

- duplicate bindings: 0;
- competing authorities: 0;
- duplicate function bodies: 0;
- import cycles: 0;
- oversized mixed-responsibility modules: 0;
- forbidden hardcoding: 0;
- legacy execution paths: 0;
- configuration-contract error: none.

The audit must also inspect duplicate parsers, validators, policies, profile expansion, service helpers, rollback helpers, evidence publishers and entrypoints.

No OpenClaw runtime access, Gateway restart, `tools.effective`, model turn or task submission is allowed before `CODE_AUDIT_PASS` on the exact current commit.

## Effective tool surface diagnostic

Authoritative plan:

`docs/DEV_EMPLOYEE_EFFECTIVE_TOOL_SURFACE_DIAGNOSTIC_PLAN_2026-06-20.md`

Entrypoint:

`scripts/dev_employee_diagnose_openclaw_effective_tool_surface.sh`

After the code gate passes, the diagnostic may run exactly once. It:

- repeats source governance and selftests;
- repeats private candidate native dry-run;
- temporarily activates only the validated read-only policy;
- calls native Gateway RPC `tools.effective` for the persisted Agent session;
- runs no model turn;
- invokes no ORIS tool;
- records only sanitized approved-tool inventory metadata;
- always restores the exact tools-denied config, marker and Skill state;
- proves final Gateway, queue, product and listener invariants;
- publishes detached-worktree evidence.

## Decision after diagnostic evidence

- approved tools absent: remediate OpenClaw optional-tool materialization or session-policy resolution;
- approved tools present: diagnose provider/model tool-call capability and Agent Harness routing without hardcoding provider/model identity;
- RPC unavailable or unsafe: rollback and stop; do not substitute direct calls or catalog inventory.

## Next action

Start a new conversation using:

`memory/dev_employee/NEXT_CHAT_HANDOFF_2026-06-20.md`

The new conversation must read GitHub context, complete and fix the code-first audit, then run the effective-tool-surface diagnostic only after the code gate passes.

Do not run `scripts/dev_employee_enable_openclaw_readonly_tools.sh`.

## Work still not completed

- native natural-language acceptance for all three read-only tools;
- approved-only non-zero `after_tool_call` telemetry;
- real privacy-safe model/tool/agent latency baseline;
- read-only P0 completion persistence;
- typed write actions with approval, RBAC, project authorization, idempotency and audit;
- generic onboarding and capability discovery;
- controlled Admin UI for Provider, Model and Policy;
- monitoring, privacy/retention, backup/restore and disaster recovery;
- multi-tenant identity, quotas, metering and commercial packaging;
- production validation.

## Commercial sequence

1. code-first audit and correction on current `main`;
2. resolve effective tool materialization or provider/model capability;
3. complete native read-only tool and telemetry acceptance;
4. establish privacy-safe real latency baselines;
5. design typed write actions only after P0 passes;
6. generic project onboarding and capability discovery;
7. controlled Admin management;
8. monitoring, privacy, backup and DR;
9. multi-tenant commercial packaging.
