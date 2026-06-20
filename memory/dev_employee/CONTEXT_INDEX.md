# ORIS Dev Employee — Authoritative Context Index

Last updated: 2026-06-20

## 1. Purpose

This is the stable entry point for every new ORIS / OpenClaw / Codex-backed AI Dev Employee commercialization conversation.

Do not reconstruct current project truth from chat history when these GitHub files are available.

The long 2026-06-20 conversation reached native read-only P0 completion. Earlier documents that describe tools-denied runtime, unresolved effective-tool materialization, provider/model tool-call uncertainty or failed three-tool acceptance are historical only.

## 2. Mandatory read order

1. `memory/dev_employee/CONTEXT_INDEX_ADDENDUM_2026-06-20.md`
2. `memory/dev_employee/CONTEXT_INDEX.md`
3. `memory/dev_employee/CURRENT_STATE_2026-06-20.md`
4. `memory/dev_employee/SESSION_ARCHIVE_COMPLETION_2026-06-20.md`
5. `memory/dev_employee/ENVIRONMENT_AND_WORKING_CONTEXT_2026-06-20.md`
6. `memory/dev_employee/current_task.json`
7. `memory/dev_employee/current_task.md`
8. `docs/DEV_EMPLOYEE_READONLY_P0_COMPLETION_AND_LATENCY_BASELINE_2026-06-20.md`
9. evidence commit `65217d4bb81f4ac3cd8c6d917af95425d2b47529`
10. `docs/DEV_EMPLOYEE_TYPED_WRITE_ACTIONS_COMMERCIAL_PHASE_PLAN_2026-06-20.md`
11. `docs/DEV_EMPLOYEE_NATIVE_SKILL_SUPPORT_TOOL_CONTRACT_2026-06-20.md`
12. `docs/DEV_EMPLOYEE_ENGINEERING_STANDARD_2026-06-16.md`
13. `docs/DEV_EMPLOYEE_ENGINEERING_STANDARD_ADDENDUM_2026-06-17.md`
14. `docs/DEV_EMPLOYEE_ENGINEERING_STANDARD_ADDENDUM_2026-06-19.md`
15. `docs/DEV_EMPLOYEE_ENVIRONMENT_AND_OPERATING_MODEL_CORRECTION_2026-06-20.md`
16. `docs/DEV_EMPLOYEE_ENVIRONMENT_AND_OPERATING_MODEL_ADDENDUM_2026-06-19.md`
17. `orchestration/project_registry.json`
18. historical archive `memory/dev_employee/SESSION_ARCHIVE_2026-06-20.md` only when deeper failure chronology is required.

Use earlier dated files only for historical background.

## 3. Authority hierarchy

When documents conflict, use this order:

1. `memory/dev_employee/CONTEXT_INDEX_ADDENDUM_2026-06-20.md`;
2. latest `memory/dev_employee/CURRENT_STATE_2026-06-20.md`;
3. `memory/dev_employee/current_task.json`;
4. `memory/dev_employee/current_task.md`;
5. `memory/dev_employee/SESSION_ARCHIVE_COMPLETION_2026-06-20.md`;
6. latest dated architecture, phase-plan, diagnostic, engineering or environment addendum;
7. current machine-readable configuration and `orchestration/project_registry.json`;
8. latest sanitized evidence under `logs/dev_employee/` and its verified evidence commit;
9. older state, handoff, diagnostic and historical archive documents.

Historical failure evidence must never be rewritten to hide failures.

## 4. Fixed commercial architecture

```text
user
  -> native OpenClaw UI and native sessions
  -> native ORIS Plugin / Agent Harness
  -> ORIS authorization, task governance, queue and evidence
  -> Codex real code execution
  -> product repository commit and tests
  -> ORIS evidence returned through OpenClaw
```

Fixed decisions:

- native OpenClaw is the commercial primary UI;
- native OpenClaw sessions are the user-facing conversation authority;
- custom ORIS UI remains restricted administration, diagnostics and rollback only;
- do not rebuild native conversation history/session features in ORIS Web Console;
- do not restore broad prompt-keyword task creation;
- expose ORIS through stable typed tools/actions/plugins;
- reuse `openclaw-gateway.service` on `127.0.0.1:18789`;
- do not reinstall or upgrade OpenClaw as generic troubleshooting;
- keep ports `18891` and `18892` loopback-only;
- keep product implementation in product repositories;
- `main` is the only mainstream branch;
- ZenMux remains excluded unless explicitly reopened;
- do not touch production host `8.136.28.6` without a separate explicit production task.

## 5. Completed predecessor task

Task id:

`commercial-openclaw-readonly-tool-enable-20260618`

Result:

`ENABLED_READONLY_AUTOMATIC_ACCEPTED`

Evidence commit:

`65217d4bb81f4ac3cd8c6d917af95425d2b47529`

Checks:

- total 26;
- pass 26;
- fail 0;
- not checked 0.

Completed boundaries:

- current code-governance findings were zero for the accepted source revision;
- effective tool materialization resolved;
- provider/model tool-call capability demonstrated;
- Agent Harness ORIS routing demonstrated;
- Free Mesh protocol version 2 preserved tool calls;
- all three read-only tools passed native natural-language acceptance;
- typed-hook telemetry passed schema, privacy, permissions and execution-outcome checks;
- read-only policy and Routing Skill were retained;
- queue and product remained unchanged;
- no write tools and no product task.

## 6. Current active task

Task id:

`commercial-openclaw-typed-write-actions-20260620`

Status:

`readonly_p0_completed_latency_baseline_v1_persisted_typed_write_actions_design_pending`

Current step:

`new_chat_audit_current_main_then_reconcile_and_implement_offline_typed_write_action_foundation`

Objective:

Design and implement the minimum generic offline foundation for typed write actions with approval, RBAC, project authorization, idempotency and audit while preserving the accepted read-only runtime and keeping write actions unregistered and disabled until a separate controlled runtime gate passes.

## 7. Current runtime truth

Plugin:

- `oris-dev-employee` `0.1.0`.

Accepted ORIS read-only tools:

- `oris_queue_status`;
- `oris_task_status`;
- `oris_latest_task_status`.

Typed hooks:

- `model_call_ended`;
- `after_tool_call`;
- `agent_end`.

Routing Skill:

- `oris-readonly-status`;
- installed;
- visible to Agent `main`.

Retained policy mode:

`profile-authority-preserved+created-profile-also-allow+skill-unrestricted`

Current safety state:

- Gateway healthy;
- queue unchanged;
- no active product task at acceptance;
- product baseline unchanged;
- read-only policy active;
- no rollback required;
- no generic exec/write tool;
- no typed write action registered or enabled;
- production untouched.

## 8. Initial privacy-safe latency baseline v1

Source:

`docs/DEV_EMPLOYEE_READONLY_P0_COMPLETION_AND_LATENCY_BASELINE_2026-06-20.md`

Observed metrics:

- model duration: count 8, min 2,661 ms, P50 5,478 ms, max 49,734 ms;
- Agent total duration: count 3, min 8,538 ms, P50 9,029 ms, max 69,134 ms;
- `oris_queue_status`: 13 ms;
- `oris_task_status`: 42 ms;
- `oris_latest_task_status`: min 13 ms, P50 27 ms, max 41 ms;
- native Skill hydration `read`: 92 ms.

TTFT is unavailable from approved typed hooks.

This is an initial observed baseline, not a commercial SLO or SLA.

## 9. Environment

- development/control/execution: `43.106.55.255`, user `admin`;
- ORIS repository: `/home/admin/projects/oris`;
- production: `8.136.28.6`, user `deploy`, do not touch;
- OpenClaw Gateway: `127.0.0.1:18789`;
- Free Mesh API: loopback `8789`;
- enqueue/status: `127.0.0.1:18891`;
- intake: `127.0.0.1:18892`;
- Web Console: `127.0.0.1:18893`;
- OpenClaw: `2026.5.19 (a185ca2)`;
- Node: `v22.22.2`;
- npm: `10.9.7`;
- Codex CLI: real coding executor;
- provider/model identity is a runtime fact and must not be hardcoded;
- PostgreSQL `oris_insight` / schema `insight` is research-only and separate from Dev Employee task state.

## 10. Engineering and interaction contract

- Chinese, professional, direct and structured;
- do not ask the user to decide routine engineering details;
- write long scripts, documents and patches directly to GitHub;
- give one short pull-and-run command only when host execution is required;
- no long heredocs;
- detailed logs under `logs/dev_employee/` and read from GitHub;
- every user-run script ends with exactly one `===== SUMMARY =====`;
- never print or commit secrets, raw config, prompts, conversation content, tool arguments/results, raw session ids or private marker content;
- user-facing shell scripts do not use `set -e`;
- inspect before editing;
- run a fresh code-first audit before the next source phase;
- remove duplicate definitions and competing authorities before feature work;
- one rule has one authoritative implementation;
- no duplicate function bodies or import cycles;
- split oversized mixed-responsibility modules;
- configuration and code remain separated;
- no hardcoded project/path/host/port/branch/provider/model/runtime/version or acceptance special case in shared code;
- generic commercial implementation only;
- detached worktrees and short-lived branches are allowed;
- competing long-lived branches are prohibited;
- do not append to tracked evidence after commit;
- completion requires real tests, local SHA, remote SHA and GitHub evidence.

## 11. Immediate next action

Use the startup prompt in:

`memory/dev_employee/NEXT_CHAT_HANDOFF_2026-06-20.md`

The new conversation must first run a fresh code-first audit on current `main`.

After the audit passes, it must inspect existing authorization, task, queue, idempotency, Plugin and Agent Harness authorities and reconcile them with:

`docs/DEV_EMPLOYEE_TYPED_WRITE_ACTIONS_COMMERCIAL_PHASE_PLAN_2026-06-20.md`

It may implement only the minimum generic offline foundation.

It must not:

- change or remove the accepted read-only policy;
- register or enable write actions;
- expose generic exec/write tools;
- submit a real product task;
- touch OpenClaw runtime during contract-only implementation;
- touch production.

## 12. Commercial priority order

1. fresh code-first audit on current `main`;
2. reconcile existing domain authorities with the typed write-action phase plan;
3. implement offline typed action schemas, identity/RBAC/project authorization, risk, approval, idempotency, task transaction and audit foundations;
4. create a separate controlled write-action runtime activation gate;
5. validate write actions on a non-product sandbox fixture before any real product task;
6. generic project onboarding and capability discovery;
7. controlled Admin Provider/Model/Policy management;
8. monitoring, privacy/retention, backup/restore, rollback and disaster recovery;
9. multi-tenant identity, quotas, metering and commercial packaging;
10. production deployment validation under a separate explicit task.
