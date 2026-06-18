# ORIS Dev Employee Environment and Operating Model Addendum — 2026-06-18

This document supersedes conflicting current-state statements in earlier environment documents. Historical evidence remains unchanged.

## 1. Hosts and repository roots

### ORIS development/control/execution host

- host: `43.106.55.255`
- Linux user: `admin`
- projects root: `/home/admin/projects`
- ORIS repository: `/home/admin/projects/oris`
- GitHub repository: `ShanGouXueHui/oris`
- mainstream branch: `main`

### Separate production host

- host: `8.136.28.6`
- Linux user: `deploy`
- rule: do not touch without an explicit deployment or production task

## 2. Public and local service topology

Public entry:

- `https://control.orisfy.com`
- Nginx provides TLS and outer access controls
- `/` serves the native OpenClaw UI
- `/admin` remains a restricted ORIS Web Console route
- `/_oris-chat-shell` remains a restricted diagnostic/rollback route

Local services:

- OpenClaw Gateway: `openclaw-gateway.service`, `127.0.0.1:18789`
- ORIS enqueue/status API: `oris-dev-employee-enqueue.service`, `127.0.0.1:18891`
- ORIS intake API: `oris-dev-employee-intake.service`, `127.0.0.1:18892`
- ORIS Web Console: `oris-dev-employee-web-console.service`, `127.0.0.1:18893`
- supervised bridge: `oris-dev-employee-bridge.service`

The intake and enqueue/status ports must remain loopback-only. Do not expose them directly through Nginx.

## 3. Approved commercial chain

```text
user
  -> native OpenClaw UI and native sessions
  -> OpenClaw native ORIS plugin / Agent Harness policy adapter
  -> ORIS task governance and evidence
  -> Codex real code execution
  -> product commit, tests and ORIS evidence returned through OpenClaw
```

Roles:

- native OpenClaw UI: primary conversation, history and session experience;
- native ORIS plugin: stable typed tools and lifecycle telemetry;
- Agent Harness: backend policy, structured output and fallback layer;
- ORIS: project authorization, task identity, queue, leases, cancellation, retry, evidence and audit;
- Codex: implementation, repair, testing, commit and controlled push;
- custom ORIS UI: restricted diagnostics/rollback only.

Do not restore broad prompt-keyword matching as the primary task creation mechanism.

## 4. OpenClaw runtime

- OpenClaw version: `2026.5.19 (a185ca2)`
- Node: `v22.22.2`
- npm: `10.9.7`
- Gateway authentication mode: token
- Control UI device pairing bypass: intentionally enabled for clients that already hold a valid Gateway credential
- OpenClaw must not be reinstalled or upgraded during the current commercialization sequence

The device-auth bypass does not disable token authentication. Never print or commit the token.

## 5. Native ORIS plugin state

Installed plugin:

- id: `oris-dev-employee`
- version: `0.1.0`
- source commit: `8f174b49196aac90b505846200ce260f75355b41`
- artifact SHA-256: `976377c2e5ffbf6932d5e43bed17c4d07cfcb16fefb7383b5ab593d4ed1eecda`
- installation evidence commit: `b831470063bc640e498d2061fdaeb2bf8bc9639c`

Registered read-only tools:

- `oris_queue_status`
- `oris_task_status`
- `oris_latest_task_status`

Registered typed hooks:

- `model_call_ended`
- `after_tool_call`
- `agent_end`

Current access state:

- plugin enabled;
- plugin errors: zero;
- the three tools remain explicitly denied pending controlled browser acceptance;
- write tools are absent;
- `tools.allow` remains unchanged;
- scoped `plugins.entries.oris-dev-employee.hooks.allowConversationAccess=true` is required for `agent_end`.

The plugin may receive conversation data through `agent_end`, but its implementation must persist only bounded duration/status fields and hashed identifiers. It must not persist messages, prompts, responses, tool arguments, tool results, headers or credentials.

Private install state:

- marker: `~/.openclaw/private/oris-dev-employee-plugin-install-current.json`
- pre-install backup: `/home/admin/.openclaw/backups/native-plugin-install-20260618T205656Z/openclaw.json.before.bak`
- both remain local-only and mode `0600`

Approved rollback entry:

- `scripts/dev_employee_rollback_openclaw_native_plugin_v2_20260618.sh`

## 6. Repositories and ownership boundaries

### ORIS platform

- GitHub: `ShanGouXueHui/oris`
- local: `/home/admin/projects/oris`
- owns platform orchestration, plugin/adapters, policy, queue, registry, documentation and intentional evidence

### Final acceptance product

- GitHub: `ShanGouXueHui/oris-final-acceptance-api`
- local: `/home/admin/projects/oris-final-acceptance-api`
- completed commit and remote main: `bcb93e17ea88704548101f5e4a5c460e15a80ec7`
- worktree baseline: clean at latest verified completion

Product code, tests and product documentation stay in product repositories. ORIS must not contain copied product implementation.

## 7. Runtime storage and databases

Dev Employee control state remains filesystem-backed and transaction-hardened:

- queue: `orchestration/dev_employee_queue/`
- intake catalog: `orchestration/dev_employee_intake_catalog/`
- task runs: `orchestration/task_runs/`
- intentional evidence: `logs/dev_employee/`
- durable context: `memory/dev_employee/` and `docs/`

Raw sessions, locks, transient plans, high-volume traces, authentication state and private plugin markers remain local and ignored.

GitHub is the durable boundary for source, decisions, approved configuration schemas, commits, remote SHA and intentional evidence. It is not the high-frequency runtime database.

Separate insight/research storage remains PostgreSQL:

- database: `oris_insight`
- schema: `insight`
- config: `config/insight_storage.json`
- bootstrap: `sql/insight_schema_v1.sql`

Do not couple Dev Employee runtime state to the insight schema without a separate architecture decision.

## 8. Models, providers and executor

- Codex CLI remains the real code executor.
- Codex non-interactive execution and systemd authentication context were previously verified.
- OpenClaw is the conversation/session runtime and plugin host.
- Model ids, provider availability, quota, latency and price are runtime facts and must be probed when needed.
- ZenMux remains excluded unless the user explicitly reopens it.

Do not hardcode one provider or one acceptance project into shared commercial logic.

## 9. Secret boundary

Local-only secrets include:

- OpenClaw token/password and device/auth state;
- Codex authentication files;
- service environment files;
- project `.env` files;
- Nginx auth data;
- TLS private keys;
- provider and product credentials;
- private plugin marker and configuration backups when they contain secret-bearing configuration.

Evidence and summaries may record only presence, mode, validation result, hashes and non-secret metadata. Never print or commit actual secret values.

## 10. Fixed interaction and execution workflow

- use Chinese, professional, direct and structured communication;
- do not ask the user to decide routine engineering details;
- write long scripts, documents and patches directly to GitHub;
- give one short command that pulls and runs a GitHub-hosted `.sh` file;
- avoid long heredocs because terminal input can be truncated;
- detailed logs go under `logs/dev_employee/` and are read from GitHub;
- each user-run script prints exactly one final `===== SUMMARY =====` block;
- the user sends only that Summary;
- user-facing Linux scripts must not use `set -e`;
- `main` is the only mainstream branch;
- backups are allowed, but competing long-lived branches are prohibited;
- do not append to the same tracked log after committing it;
- use detached worktrees for evidence when the main worktree is intentionally dirty.

## 11. Current minimum safe action

Before enabling the three read-only tools:

1. run a read-only readiness check against the private marker, backup, current plugin runtime and effective tool policy;
2. verify Gateway/public UI, queue, product baseline and private listeners;
3. verify the telemetry target is local, private and contains no historical secret/message data;
4. create a reversible enable script in GitHub;
5. modify only the approved tool policy entries;
6. execute direct and browser smoke tests;
7. return automatically to the tools-denied state on any failure.
