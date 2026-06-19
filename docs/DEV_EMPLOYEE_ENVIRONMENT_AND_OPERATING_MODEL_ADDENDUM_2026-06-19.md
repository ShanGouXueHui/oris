# ORIS Dev Employee Environment and Operating Model Addendum — 2026-06-19

This document supersedes conflicting current-environment and working-model statements in the 2026-06-18 environment addendum. Historical evidence remains unchanged.

## 1. Hosts and repository roots

### ORIS development/control/execution host

- host: `43.106.55.255`
- Linux user: `admin`
- projects root: `/home/admin/projects`
- ORIS local repository: `/home/admin/projects/oris`
- ORIS GitHub repository: `ShanGouXueHui/oris`
- mainstream branch: `main`

### Separate production host

- host: `8.136.28.6`
- Linux user: `deploy`
- rule: do not touch without an explicit production or deployment task

Development and production roles must not be silently mixed.

## 2. Public and local topology

Public entry:

- `https://control.orisfy.com`
- Nginx supplies TLS and outer access controls
- `/` serves native OpenClaw
- `/admin` is a restricted ORIS administrative/diagnostic route
- `/_oris-chat-shell` is a restricted rollback/diagnostic route

Local services:

- OpenClaw Gateway: `openclaw-gateway.service`, `127.0.0.1:18789`
- ORIS enqueue/status API: `127.0.0.1:18891`
- ORIS intake API: `127.0.0.1:18892`
- ORIS Web Console: `127.0.0.1:18893`
- supervised bridge: `oris-dev-employee-bridge.service`

Ports 18891 and 18892 must remain loopback-only and must not be exposed through Nginx.

## 3. Approved commercial chain

```text
user
  -> native OpenClaw UI and native sessions
  -> native ORIS plugin / Agent Harness policy adapter
  -> ORIS task governance and evidence
  -> Codex real code execution
  -> product commit, tests and ORIS evidence returned through OpenClaw
```

Responsibilities:

- OpenClaw: conversation, sessions, model execution and plugin host;
- native ORIS plugin: typed tools and privacy-safe lifecycle telemetry;
- Agent Harness: backend policy/schema/routing adapter;
- ORIS: project authorization, task identity, queue, leases, retry/cancel semantics, evidence and audit;
- Codex CLI: real implementation, testing, repair, commit and controlled push;
- custom ORIS UI: restricted diagnostics and rollback only.

Broad prompt-keyword task creation remains prohibited.

## 4. Runtime versions and upgrade policy

- OpenClaw: `2026.5.19 (a185ca2)`
- Node: `v22.22.2`
- npm: `10.9.7`
- Gateway authentication: token
- Codex CLI: real coding executor

Do not reinstall or upgrade OpenClaw during the active read-only enablement task.

Do not reinstall the ORIS plugin as a generic troubleshooting step.

## 5. Native plugin baseline

Installed plugin:

- id: `oris-dev-employee`
- version: `0.1.0`
- source commit: `8f174b49196aac90b505846200ce260f75355b41`
- artifact SHA-256: `976377c2e5ffbf6932d5e43bed17c4d07cfcb16fefb7383b5ab593d4ed1eecda`
- installation evidence: `b831470063bc640e498d2061fdaeb2bf8bc9639c`

Registered read-only tools:

- `oris_queue_status`
- `oris_task_status`
- `oris_latest_task_status`

Registered typed hooks:

- `model_call_ended`
- `after_tool_call`
- `agent_end`

The current runtime must be treated as restored to the tools-denied baseline after the latest healthy rollback.

No submit/cancel/retry tool is authorized in the current task.

## 6. Repositories and ownership boundaries

### ORIS platform

Owns:

- platform orchestration;
- plugin and runtime adapters;
- task lifecycle and queue;
- policy/config/schema;
- project registry;
- durable context;
- intentional evidence.

### Product repositories

Own:

- product source;
- product tests;
- product documentation;
- product commits and deployment artifacts.

Completed acceptance product:

- GitHub: `ShanGouXueHui/oris-final-acceptance-api`
- local: `/home/admin/projects/oris-final-acceptance-api`
- completed product/remote commit: `bcb93e17ea88704548101f5e4a5c460e15a80ec7`

Do not copy product implementation into ORIS.

## 7. Runtime state, evidence and database

Dev Employee operational state remains filesystem-backed and transaction-hardened:

- queue: `orchestration/dev_employee_queue/`
- intake catalog: `orchestration/dev_employee_intake_catalog/`
- task runs: `orchestration/task_runs/`
- promoted evidence: `logs/dev_employee/`
- durable context: `memory/dev_employee/` and `docs/`
- project authority: `orchestration/project_registry.json`

Raw sessions, locks, temporary plans, authentication state, high-volume traces and private markers remain local/ignored.

GitHub is the durable source/decision/evidence boundary. It is not the high-frequency task database.

Separate research storage:

- PostgreSQL database: `oris_insight`
- schema: `insight`
- role: research/insight storage only
- latest security result: `ALREADY_SECURE_AND_VERIFIED`
- latest evidence commit: `bc799a640138a19800270ecab1a656f09d70252a`

Do not couple Dev Employee task state to `oris_insight` without a new architecture decision.

## 8. Models and providers

- OpenClaw controls the conversation model/provider path.
- Codex CLI controls real coding execution.
- Provider/model identity, availability, quota, latency and cost are runtime facts.
- Shared code must not hardcode a provider or model.
- Version/provider-specific compatibility belongs in one validated configuration authority.
- Privacy-safe telemetry may record bounded provider/model identifiers.
- Telemetry may not record prompts, messages, assistant text, tool arguments/results, headers, cookies, tokens or credentials.
- ZenMux remains excluded unless the user explicitly reopens it.

## 9. Secret boundary

Local-only secrets include:

- OpenClaw token/password/device/auth state;
- Codex authentication files;
- service environment files;
- product `.env` files;
- Nginx auth data;
- TLS private keys;
- provider/product/database credentials;
- private plugin markers and secret-bearing backups.

Evidence may record only presence, validation status, mode, bounded non-secret metadata and hashes.

Never print or commit actual secret values or raw config.

## 10. Fixed interaction workflow

- communicate in Chinese, professionally, directly and structurally;
- do not ask the user to decide routine engineering details;
- write long scripts, patches and documents directly to GitHub;
- when host execution is required, give one short pull-and-run command;
- do not give long heredocs because the terminal channel can truncate them;
- write verbose output to `logs/dev_employee/`;
- inspect detailed logs from GitHub instead of asking the user to paste them;
- every user-run script prints exactly one final `===== SUMMARY =====` block;
- the user sends only the Summary;
- user-facing shell scripts do not use `set -e`;
- do not append to a tracked evidence log after commit;
- use detached worktrees for evidence commits when needed;
- never expose secrets in Summary, GitHub or chat.

## 11. Engineering workflow

Before modifying a file:

1. scan the target scope for duplicate definitions and existing authoritative implementations;
2. scan for hardcoded environment/project/provider/model/acceptance values;
3. identify the authoritative rule/config source;
4. split oversized mixed-responsibility files when needed;
5. make the minimum generic commercial change;
6. run target and regression tests;
7. validate with the real installed runtime where applicable;
8. publish sanitized evidence.

Authoritative engineering addendum:

`docs/DEV_EMPLOYEE_ENGINEERING_STANDARD_ADDENDUM_2026-06-19.md`

## 12. Branch and backup policy

- `main` is the only mainstream branch.
- Private backups, commits, tags and detached evidence worktrees are allowed.
- Competing long-lived branches are prohibited.
- Completion requires local/remote SHA verification and durable evidence.

## 13. Current minimum safe action

Do not rerun the dual-stage enablement blindly.

First diagnose why the candidate configuration prevented Gateway health by:

- building it privately;
- validating it with the installed OpenClaw runtime;
- checking duplicate/unsupported tool-policy entries;
- capturing bounded sanitized service diagnostics on controlled failure;
- restoring the exact tools-denied config;
- proving Gateway health;
- publishing tri-state evidence.

Authoritative plan:

`docs/DEV_EMPLOYEE_OPENCLAW_READONLY_ENABLEMENT_DIAGNOSTIC_PLAN_2026-06-19.md`
