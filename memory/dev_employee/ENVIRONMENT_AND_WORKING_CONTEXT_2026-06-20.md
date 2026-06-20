# ORIS Dev Employee Environment and Working Context Snapshot — 2026-06-20

## 1. Scope

This file is the current compact environment, system-boundary and interaction snapshot for new conversations. It complements the detailed environment addendum and does not replace historical evidence.

## 2. Hosts

### Development/control/execution

- host: `43.106.55.255`;
- user: `admin`;
- projects root: `/home/admin/projects`;
- ORIS repo: `/home/admin/projects/oris`;
- GitHub repo: `ShanGouXueHui/oris`;
- only mainstream branch: `main`.

### Production

- host: `8.136.28.6`;
- user: `deploy`;
- rule: do not touch unless a separate explicit production task is created.

Development and production responsibilities must never be silently mixed.

## 3. Public and local services

Public:

- `https://control.orisfy.com`;
- `/`: native OpenClaw UI;
- `/admin`: restricted ORIS administration/diagnostics;
- `/_oris-chat-shell`: restricted rollback/diagnostics.

Local:

- OpenClaw Gateway: `openclaw-gateway.service`, `127.0.0.1:18789`;
- ORIS enqueue/status: `127.0.0.1:18891`;
- ORIS intake: `127.0.0.1:18892`;
- ORIS Web Console: `127.0.0.1:18893`;
- bridge: `oris-dev-employee-bridge.service`.

Ports 18891 and 18892 must remain loopback-only and must not be exposed through Nginx.

## 4. Runtime and model stack

- OpenClaw: `2026.5.19 (a185ca2)`;
- Node: `v22.22.2`;
- npm: `10.9.7`;
- Codex CLI: real coding executor;
- OpenClaw controls the conversation provider/model;
- Provider/model identity is a runtime fact and must not be hardcoded;
- ZenMux is excluded unless explicitly reopened.

Current observed model telemetry from the latest failed acceptance recorded bounded identifiers only. Do not infer permanent provider/model configuration from one evidence run.

## 5. Plugin and tool state

Plugin:

- id: `oris-dev-employee`;
- version: `0.1.0`;
- source commit: `8f174b49196aac90b505846200ce260f75355b41`;
- installation result: `INSTALLED_TOOLS_DENIED`.

Read-only tools:

- `oris_queue_status`;
- `oris_task_status`;
- `oris_latest_task_status`.

Typed hooks:

- `model_call_ended`;
- `after_tool_call`;
- `agent_end`.

Current runtime after the latest rollback must be treated as the exact healthy tools-denied baseline.

No write tool is authorized.

## 6. Repositories and ownership

### ORIS platform

Owns platform orchestration, task lifecycle, policy, adapters, plugin integration, durable context and intentional evidence.

### Product repositories

Own product source, tests, product documentation and product commits.

Final acceptance product:

- repo: `ShanGouXueHui/oris-final-acceptance-api`;
- local: `/home/admin/projects/oris-final-acceptance-api`;
- baseline commit: `bcb93e17ea88704548101f5e4a5c460e15a80ec7`.

Do not move or duplicate product implementation into ORIS.

Project boundaries are governed by `orchestration/project_registry.json`.

## 7. Operational state and database

Operational Dev Employee state:

- `orchestration/dev_employee_queue/`;
- `orchestration/dev_employee_intake_catalog/`;
- `orchestration/task_runs/`;
- `logs/dev_employee/`;
- `memory/dev_employee/`;
- `docs/`.

Research database:

- database: `oris_insight`;
- schema: `insight`;
- role: research/insight only;
- security: `ALREADY_SECURE_AND_VERIFIED`;
- evidence: `bc799a640138a19800270ecab1a656f09d70252a`.

Do not move Dev Employee queue/task truth into PostgreSQL without a new architecture decision.

## 8. Secret and privacy boundary

Local-only secrets include OpenClaw auth state, Codex auth, service environment files, product `.env`, Nginx auth, TLS keys, database/provider credentials, private plugin markers and secret-bearing backups.

Allowed evidence:

- presence or validation status;
- bounded counts;
- non-secret mode names;
- hashes;
- bounded provider/model identifiers where explicitly permitted.

Forbidden evidence:

- raw config;
- token/password/key values;
- prompts or messages;
- assistant responses;
- tool arguments or tool results;
- headers, cookies or auth state;
- raw private marker content;
- raw session identifiers.

## 9. Interaction preferences

- use Chinese;
- professional, direct and structured;
- no praise-driven or emotional filler;
- do not ask the user to choose routine engineering implementation details;
- write long code, scripts, patches and documents directly into GitHub;
- provide only one short pull-and-run command when host execution is required;
- do not use long heredocs;
- read detailed logs from GitHub;
- user returns only the final Summary;
- every execution script prints exactly one `===== SUMMARY =====`;
- do not use `set -e` in user-facing Linux scripts;
- never request or expose tokens, SSH private keys, passwords or full account credentials.

## 10. Engineering preferences

- inspect before editing;
- duplicate functions, variables, classes, parsers, policies and helpers must be removed before feature work;
- one rule has one authoritative implementation;
- configuration and code remain separated;
- large files are split by responsibility;
- changes are generic commercial implementations, not acceptance-project special cases;
- temporary backups and detached worktrees are allowed;
- no competing long-lived branches;
- completed work requires real tests, commit SHA, remote SHA and sanitized evidence;
- do not append to tracked evidence logs after commit.

## 11. Current continuation boundary

The latest native Agent run completed three model turns but emitted zero tool calls. Direct tool invocation and plugin inventory passed. A native effective-tool-surface diagnostic is prepared but must not run until a fresh code-first audit on current `main` passes.

Authoritative current state:

- `memory/dev_employee/CURRENT_STATE_2026-06-20.md`;
- `memory/dev_employee/current_task.json`;
- `memory/dev_employee/SESSION_ARCHIVE_2026-06-20.md`;
- `docs/DEV_EMPLOYEE_CODE_FIRST_CONTINUATION_GATE_2026-06-20.md`;
- `docs/DEV_EMPLOYEE_EFFECTIVE_TOOL_SURFACE_DIAGNOSTIC_PLAN_2026-06-20.md`.
