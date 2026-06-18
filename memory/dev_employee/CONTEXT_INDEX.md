# ORIS Dev Employee — Authoritative Context Index

Last updated: 2026-06-18

## Purpose

This is the stable entry point for every new ORIS / OpenClaw / Codex-backed AI Dev Employee conversation.

Do not reconstruct current project truth from chat history when these GitHub files are available.

## Mandatory read order

Read the current authoritative set first:

1. `memory/dev_employee/CURRENT_STATE_2026-06-18.md`
2. `memory/dev_employee/SESSION_ARCHIVE_2026-06-18.md`
3. `memory/dev_employee/OPENCLAW_NATIVE_PLUGIN_INSTALL_COMPLETION_2026-06-18.md`
4. `memory/dev_employee/current_task.json`
5. `memory/dev_employee/current_task.md`
6. `docs/DEV_EMPLOYEE_ENVIRONMENT_AND_OPERATING_MODEL_ADDENDUM_2026-06-18.md`
7. `docs/DEV_EMPLOYEE_OPENCLAW_AGENT_END_POLICY_ADDENDUM_2026-06-18.md`
8. `docs/DEV_EMPLOYEE_OPENCLAW_PLUGIN_RUNTIME_HOOK_INSPECTION_ADDENDUM_2026-06-18.md`
9. `docs/DEV_EMPLOYEE_COMMERCIALIZATION_PRIORITY_2026-06-18.md`
10. `docs/DEV_EMPLOYEE_ENGINEERING_STANDARD_2026-06-16.md`
11. `docs/DEV_EMPLOYEE_ENGINEERING_STANDARD_ADDENDUM_2026-06-17.md`
12. `docs/DEV_EMPLOYEE_QUEUE_LIFECYCLE_HARDENING_2026-06-16.md`
13. `orchestration/project_registry.json`
14. `memory/dev_employee/NEXT_CHAT_HANDOFF_2026-06-18.md`
15. `memory/dev_employee/NEW_CHAT_BOOTSTRAP_PROMPT_2026-06-18.md`

Use earlier files only for historical background.

## Authority hierarchy

When documents conflict, use this order:

1. latest dated file under `memory/dev_employee/`;
2. `memory/dev_employee/current_task.json`;
3. latest dated architecture/decision/addendum documents;
4. current machine-readable configuration and project registry;
5. latest sanitized task/evidence under `orchestration/task_runs/` and `logs/dev_employee/`;
6. older dated state, handoff and architecture documents.

Historical evidence must not be rewritten to hide failures. Correct current truth with a newer authoritative document or an explicit correction addendum.

## Current commercial architecture

Approved chain:

```text
user
  -> native OpenClaw UI and native sessions
  -> native ORIS plugin / Agent Harness policy adapter
  -> ORIS control plane and task governance
  -> Codex real code execution
  -> product commit/tests and ORIS evidence returned to OpenClaw
```

Fixed decisions:

- native OpenClaw is the commercial primary UI;
- custom ORIS UI remains restricted diagnostics/rollback only;
- do not reinstall or upgrade OpenClaw during the current commercialization sequence;
- reuse `openclaw-gateway.service` on `127.0.0.1:18789`;
- expose ORIS through stable typed tools/actions/plugins;
- do not restore broad prompt-keyword matching as the primary task-creation mechanism;
- keep `/admin` and `/_oris-chat-shell` restricted;
- keep enqueue/status and intake private;
- keep product code in product repositories.

## Completed milestones

### Native UI and sessions

Completed:

- root migrated to native OpenClaw;
- token-authenticated native UI accepted;
- new conversation, multiple sessions, history switching and refresh persistence accepted;
- session deletion accepted with another session preserved;
- restricted admin and rollback routes accepted;
- device pairing intentionally bypassed for clients with a valid Gateway credential;
- OpenClaw not reinstalled or upgraded.

### Final acceptance product

Repository:

`ShanGouXueHui/oris-final-acceptance-api`

Final product commit and remote main:

`bcb93e17ea88704548101f5e4a5c460e15a80ec7`

The `/capabilities` implementation, tests and README API list are complete. Do not rerun this task without regression evidence.

### Native plugin validation

The `oris-dev-employee` mixed plugin passed strict build, unit tests, mixed-plugin runtime contract, manifest, runtime import, static safety and loopback API checks without installation.

Validation evidence commit:

`fadb6275f0a348aed7692f4a910f341f69049363`

### Native plugin installation

Installation task:

`commercial-openclaw-native-plugin-install-20260618`

Final result:

`INSTALLED_TOOLS_DENIED`

Installed source commit:

`8f174b49196aac90b505846200ce260f75355b41`

Artifact SHA-256:

`976377c2e5ffbf6932d5e43bed17c4d07cfcb16fefb7383b5ab593d4ed1eecda`

Installation evidence commit:

`b831470063bc640e498d2061fdaeb2bf8bc9639c`

Runtime-verified tools:

- `oris_queue_status`
- `oris_task_status`
- `oris_latest_task_status`

Runtime-verified hooks:

- `model_call_ended`
- `after_tool_call`
- `agent_end`

Current plugin policy:

- plugin enabled;
- plugin errors: zero;
- three tools still explicitly denied;
- write tools absent;
- `tools.allow` unchanged at installation;
- scoped `allowConversationAccess=true` enabled for the ORIS plugin;
- Gateway authentication mode and credential unchanged at installation.

Do not reinstall the plugin.

## Current active task

Task id:

`commercial-openclaw-readonly-tool-enable-20260618`

Status:

`plugin_installed_tools_denied_pending_controlled_enable`

Current step:

`read_only_readiness_before_readonly_tool_enable`

Immediate action:

- create a GitHub-hosted read-only readiness script;
- inspect effective deny/allow/profile/agent tool policy;
- validate marker, backup, plugin runtime, telemetry safety, Gateway, queue and product baseline;
- do not mutate configuration or restart services during readiness discovery;
- after reading evidence, build a reversible enablement and browser-smoke script;
- keep write tools absent and return to tools-denied state on failure.

## Current environment

### Hosts

- ORIS control/development/execution: `43.106.55.255`, user `admin`
- ORIS repository: `/home/admin/projects/oris`
- separate production host: `8.136.28.6`, user `deploy`; do not touch without an explicit production task

### Services and ports

- native OpenClaw Gateway: `127.0.0.1:18789`
- ORIS enqueue/status: `127.0.0.1:18891`
- ORIS intake: `127.0.0.1:18892`
- ORIS Web Console: `127.0.0.1:18893`
- bridge: `oris-dev-employee-bridge.service`

The 18891 and 18892 listeners remain loopback-only.

### Runtime versions

- OpenClaw: `2026.5.19 (a185ca2)`
- Node: `v22.22.2`
- npm: `10.9.7`
- Codex CLI: real coding executor

### Storage

- queue: `orchestration/dev_employee_queue/`
- intake catalog: `orchestration/dev_employee_intake_catalog/`
- task runs: `orchestration/task_runs/`
- intentional evidence: `logs/dev_employee/`
- durable context: `memory/dev_employee/` and `docs/`
- separate research storage: PostgreSQL `oris_insight`, schema `insight`

GitHub is the durable source/evidence boundary, not the high-frequency runtime database.

## Corrected operational lessons

- `openclaw plugins validate` is not the correct validator for the mixed plugin;
- runtime typed hooks must be read from `typedHooks`;
- `agent_end` requires scoped `allowConversationAccess=true` for a non-bundled plugin;
- automated plugin uninstall must use `--force`;
- a hidden interactive prompt can look like a hung script when output is redirected;
- the 18891 `/latest` 404 was a stale process, not missing source;
- do not append to a tracked log after committing it;
- use detached worktrees for evidence when the main worktree is intentionally dirty;
- verify exact runtime state, not only CLI/UI success text.

## Fixed engineering and interaction contract

- Chinese, professional, direct and structured;
- do not ask the user to decide routine engineering details;
- write long scripts/docs/patches directly to GitHub;
- give one short pull-and-run command;
- avoid long heredocs because terminal input can be truncated;
- detailed logs go under `logs/dev_employee/` and are inspected from GitHub;
- every user-run script ends with one `===== SUMMARY =====` block;
- the user sends only the Summary;
- never print or commit secrets;
- user-facing Linux scripts must not use `set -e`;
- `main` is the only mainstream branch;
- backups allowed, competing long-lived branches prohibited;
- ORIS owns platform/evidence; product repositories own product code/tests/docs;
- layered decoupling and configuration separation;
- one rule has one authoritative source;
- build generic commercial mechanisms, not acceptance-project special cases;
- completion requires deliverables, real tests, local SHA, remote SHA and ORIS evidence.

## Historical context

These remain useful as history but are superseded for current operations where they conflict with 2026-06-18 files:

- `memory/dev_employee/CURRENT_STATE_2026-06-17_NATIVE_UI_COMPLETED.md`
- `memory/dev_employee/NEXT_CHAT_HANDOFF_2026-06-17_NATIVE_UI_COMPLETED.md`
- `memory/dev_employee/CURRENT_STATE_2026-06-17.md`
- `memory/dev_employee/SESSION_ARCHIVE_2026-06-17.md`
- `memory/dev_employee/NEXT_CHAT_HANDOFF_2026-06-17.md`
- `memory/dev_employee/NEW_CHAT_BOOTSTRAP_PROMPT_2026-06-17.md`
- older environment statements that say the custom Web Console is still the root UI;
- older statements that the final acceptance README gap is still open;
- old installation conclusions that count hooks without `typedHooks` or omit the `agent_end` policy requirement.
