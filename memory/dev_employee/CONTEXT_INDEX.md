# ORIS Dev Employee — Authoritative Context Index

Last updated: 2026-06-19

## Purpose

This is the stable entry point for every new ORIS / OpenClaw / Codex-backed AI Dev Employee conversation.

Do not reconstruct current project truth from chat history when these GitHub files are available.

## Mandatory read order

Read the current authoritative set first:

1. `memory/dev_employee/CURRENT_STATE_2026-06-19.md`
2. `memory/dev_employee/SESSION_ARCHIVE_2026-06-19.md`
3. `memory/dev_employee/current_task.json`
4. `memory/dev_employee/current_task.md`
5. `docs/DEV_EMPLOYEE_OPENCLAW_READONLY_ENABLEMENT_DIAGNOSTIC_PLAN_2026-06-19.md`
6. `docs/DEV_EMPLOYEE_ENVIRONMENT_AND_OPERATING_MODEL_ADDENDUM_2026-06-19.md`
7. `docs/DEV_EMPLOYEE_ENGINEERING_STANDARD_2026-06-16.md`
8. `docs/DEV_EMPLOYEE_ENGINEERING_STANDARD_ADDENDUM_2026-06-17.md`
9. `docs/DEV_EMPLOYEE_ENGINEERING_STANDARD_ADDENDUM_2026-06-19.md`
10. `memory/dev_employee/OPENCLAW_NATIVE_PLUGIN_INSTALL_COMPLETION_2026-06-18.md`
11. `docs/DEV_EMPLOYEE_OPENCLAW_AGENT_END_POLICY_ADDENDUM_2026-06-18.md`
12. `docs/DEV_EMPLOYEE_OPENCLAW_PLUGIN_RUNTIME_HOOK_INSPECTION_ADDENDUM_2026-06-18.md`
13. `docs/DEV_EMPLOYEE_COMMERCIALIZATION_PRIORITY_2026-06-18.md`
14. `orchestration/project_registry.json`
15. `memory/dev_employee/NEXT_CHAT_HANDOFF_2026-06-19.md`
16. `memory/dev_employee/NEW_CHAT_BOOTSTRAP_PROMPT_2026-06-19.md`
17. latest failed-attempt evidence commit `c68e7d2f50a84f6e68199d2fada9a244f31e4f41`

Use earlier dated files only for historical background.

## Authority hierarchy

When documents conflict, use this order:

1. latest dated file under `memory/dev_employee/`;
2. `memory/dev_employee/current_task.json`;
3. latest dated architecture/decision/engineering/environment addendum;
4. current machine-readable configuration and `orchestration/project_registry.json`;
5. latest sanitized evidence under `logs/dev_employee/` and its remote evidence commit;
6. older dated state, handoff and architecture documents.

Historical evidence must never be rewritten to hide failures. Correct current truth with a newer authoritative document or explicit correction addendum.

## Current commercial architecture

```text
user
  -> native OpenClaw UI and native sessions
  -> native ORIS plugin / Agent Harness policy adapter
  -> ORIS task governance and evidence
  -> Codex real code execution
  -> product commit, tests and ORIS evidence returned through OpenClaw
```

Fixed decisions:

- native OpenClaw is the commercial primary UI;
- custom ORIS UI remains restricted diagnostics/rollback only;
- do not reinstall or upgrade OpenClaw during the active task;
- reuse `openclaw-gateway.service` on `127.0.0.1:18789`;
- expose ORIS through stable typed tools/actions/plugins;
- do not restore broad prompt-keyword task creation;
- keep `/admin` and `/_oris-chat-shell` restricted;
- keep 18891 and 18892 loopback-only;
- keep product code in product repositories;
- `main` is the only mainstream branch.

## Completed milestones

### Native UI and sessions

Completed:

- native OpenClaw root;
- token-authenticated UI;
- new/multiple conversations;
- history switching and refresh persistence;
- session deletion;
- restricted admin and rollback routes.

### Final acceptance product

Repository:

`ShanGouXueHui/oris-final-acceptance-api`

Completed product and remote-main commit:

`bcb93e17ea88704548101f5e4a5c460e15a80ec7`

### Native plugin validation and installation

Plugin:

- id: `oris-dev-employee`
- version: `0.1.0`
- installed source: `8f174b49196aac90b505846200ce260f75355b41`
- artifact SHA-256: `976377c2e5ffbf6932d5e43bed17c4d07cfcb16fefb7383b5ab593d4ed1eecda`
- installation result: `INSTALLED_TOOLS_DENIED`
- installation evidence: `b831470063bc640e498d2061fdaeb2bf8bc9639c`

Runtime-verified tools:

- `oris_queue_status`
- `oris_task_status`
- `oris_latest_task_status`

Runtime-verified typed hooks:

- `model_call_ended`
- `after_tool_call`
- `agent_end`

No write tool is authorized in the active task.

### Read-only readiness

- result: `READY`
- checks: 26/26 pass
- evidence commit: `a63dd823ac4d5b3fa0fa867771f94904d0b4ceee`

## Current active task

Task id:

`commercial-openclaw-readonly-tool-enable-20260618`

Status:

`blocked_after_dual_stage_policy_gateway_health_failure_rollback_complete`

Current step:

`diagnose_gateway_rejection_of_dual_stage_readonly_policy_before_retry`

## Current progress and blocker

Previously proved:

- direct calls to all three read-only tools pass;
- managed routing skill was runtime-visible to Agent `main`;
- native Agent/Gateway transport and persisted sessions work;
- earlier model runs completed with `model_call_ended=3`, `agent_end=3`, `after_tool_call=0`;
- direct tool success and skill visibility do not prove model tool materialization/invocation.

The current source implements reversible dual-stage authorization for optional-tool materialization and active-profile extension.

Relevant commits:

- `741f24687c751ebfa405d8ea74c8a45a53a09161`
- `0182858e58fefdb267f7cb3cf8b76bf6a8064323`
- `c48a8741645cfd57ba24530a6dc4da767612568a`
- `d650a0f9e4686df4b46157ace680e9bb08e396ff`

Latest attempt:

- failure: `RuntimeError:existing OpenClaw Gateway did not become healthy`
- policy mode: `materialized-profile-plus-approved+created-profile-also-allow+skill-unrestricted`
- rollback healthy: yes
- evidence commit: `c68e7d2f50a84f6e68199d2fada9a244f31e4f41`

The failure happened after candidate policy activation and before runtime inventory/direct calls/native Agent acceptance.

Current runtime is treated as restored to the tools-denied baseline.

The blocker is the missing installed-runtime validation/journal reason for Gateway rejecting or failing under the candidate policy.

Do not rerun the same enablement blindly.

## Immediate next action

Follow:

`docs/DEV_EMPLOYEE_OPENCLAW_READONLY_ENABLEMENT_DIAGNOSTIC_PLAN_2026-06-19.md`

The next change must:

1. scan target files for duplicate definitions, existing helpers and hardcoded values;
2. build candidate config privately;
3. run installed OpenClaw config/schema validation where supported;
4. validate the actual compatibility of `profile`, `allow`, `alsoAllow`, group selectors and optional plugin tools;
5. capture bounded sanitized Gateway status/journal evidence before rollback on failure;
6. use `PASS`/`FAIL`/`NOT_CHECKED` evidence semantics;
7. restore and prove exact tools-denied Gateway health;
8. publish sanitized evidence through a detached worktree;
9. choose the next policy only from observed runtime evidence.

## Current environment

### Hosts

- ORIS development/control/execution: `43.106.55.255`, user `admin`
- ORIS repository: `/home/admin/projects/oris`
- separate production host: `8.136.28.6`, user `deploy`; do not touch without an explicit production task

### Services

- OpenClaw Gateway: `127.0.0.1:18789`
- enqueue/status: `127.0.0.1:18891`
- intake: `127.0.0.1:18892`
- Web Console: `127.0.0.1:18893`
- bridge: `oris-dev-employee-bridge.service`

### Runtime and data

- OpenClaw: `2026.5.19 (a185ca2)`
- Node: `v22.22.2`
- npm: `10.9.7`
- Codex CLI: real coding executor
- Dev Employee state: filesystem-backed and transaction-hardened
- research storage: PostgreSQL `oris_insight`, schema `insight`
- latest database security result: `ALREADY_SECURE_AND_VERIFIED`
- latest database evidence: `bc799a640138a19800270ecab1a656f09d70252a`
- provider/model availability and identity are runtime facts, not hardcoded constants
- ZenMux remains excluded unless explicitly reopened

## Engineering and interaction contract

- Chinese, professional, direct and structured;
- do not ask the user to decide routine engineering details;
- write long scripts/docs/patches directly to GitHub;
- give one short pull-and-run command only when host execution is required;
- no long heredocs;
- detailed logs go under `logs/dev_employee/` and are read from GitHub;
- every user-run script ends with exactly one `===== SUMMARY =====`;
- user sends only the Summary;
- never print or commit secrets/raw config/private marker content;
- user-facing shell scripts do not use `set -e`;
- scan for duplicate definitions and hardcoded values before every edit;
- reuse one authoritative definition per rule;
- split large files by responsibility;
- layered decoupling and configuration separation are mandatory;
- generic commercial implementation only;
- backups and detached worktrees allowed;
- competing long-lived branches prohibited;
- do not append to tracked logs after commit;
- completion requires deliverables, real tests, local/remote SHA and durable evidence.

Authoritative engineering update:

`docs/DEV_EMPLOYEE_ENGINEERING_STANDARD_ADDENDUM_2026-06-19.md`

## Commercial priority order

1. diagnose and resolve Gateway rejection of the read-only candidate policy;
2. complete native natural-language acceptance of exactly three read-only tools;
3. establish privacy-safe real latency telemetry;
4. design explicit typed write actions only after P0 passes;
5. add generic project onboarding and capability discovery;
6. add controlled Admin provider/policy management;
7. add monitoring, privacy/retention, backup/restore and disaster recovery;
8. add multi-tenant quotas, metering and commercial packaging.

## Superseded current-operation documents

The following remain historical but are superseded where they conflict with 2026-06-19 files:

- `memory/dev_employee/CURRENT_STATE_2026-06-18.md`
- `memory/dev_employee/SESSION_ARCHIVE_2026-06-18.md`
- `memory/dev_employee/NEXT_CHAT_HANDOFF_2026-06-18.md`
- `memory/dev_employee/NEW_CHAT_BOOTSTRAP_PROMPT_2026-06-18.md`
- `docs/DEV_EMPLOYEE_ENVIRONMENT_AND_OPERATING_MODEL_ADDENDUM_2026-06-18.md`

The 2026-06-18 plugin installation completion and hook-policy documents remain authoritative for installation history and runtime-hook requirements.
