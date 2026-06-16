# ORIS Dev Employee Environment Addendum — 2026-06-17

This file supersedes conflicting runtime statements in `docs/DEV_EMPLOYEE_ENVIRONMENT_AND_OPERATING_MODEL_2026-06-16.md`.

## Current hosts

### ORIS development/control/execution host

- IP: `43.106.55.255`
- user: `admin`
- projects root: `/home/admin/projects`
- ORIS repo: `/home/admin/projects/oris`
- GitHub owner: `ShanGouXueHui`
- mainstream branch: `main`

### Separate production host

- IP: `8.136.28.6`
- user: `deploy`
- rule: do not touch without an explicit production/deployment task

## Public entry and edge

- public domain: `https://control.orisfy.com`
- DNS target: ORIS host
- TLS and outer Basic Auth: Nginx
- intake port must remain loopback-only

Current root route serves the custom ORIS Web Console v5. This is temporary. The approved target is the existing native OpenClaw Gateway UI.

Before switching routes:

- inspect effective config with `nginx -T`;
- patch only the first effective matching server block;
- preserve WebSocket upgrade headers;
- preserve OpenClaw token/device-pairing behavior;
- preserve restricted `/admin`;
- retain a non-default rollback route for the custom shell;
- back up config, run `nginx -t`, reload only after validation, and roll back on failure.

## Local services

- OpenClaw Gateway: `openclaw-gateway.service`, `127.0.0.1:18789`, active
- custom Web Console v5: `oris-dev-employee-web-console.service`, `127.0.0.1:18893`, active
- intake/status v2: `oris-dev-employee-intake.service`, `127.0.0.1:18892`, active
- supervised bridge v3: `oris-dev-employee-bridge.service`, active

Target roles:

- native OpenClaw UI: primary conversation/session experience;
- Agent Harness: backend tool/policy adapter;
- ORIS: task lifecycle, queue, authorization and evidence;
- Codex: implementation, tests, commit and push;
- custom Web Console: restricted diagnostic/rollback surface only.

OpenClaw must not be reinstalled or upgraded during this migration.

## Repositories

### Platform

- repo: `ShanGouXueHui/oris`
- local: `/home/admin/projects/oris`
- owns platform orchestration, tools/adapters, queue, policy, registry, docs and evidence

### Acceptance product

- repo: `ShanGouXueHui/oris-final-acceptance-api`
- local: `/home/admin/projects/oris-final-acceptance-api`
- latest observed feature commit: `927f1968cc86bfd5213670f4eaa171fc1a3be620`
- known gap: requested README API-list update is missing

Product code stays in product repositories. ORIS platform code stays in ORIS.

## Runtime storage and databases

Current Dev Employee runtime remains filesystem-backed but transaction-hardened:

- queue: `orchestration/dev_employee_queue/`
- intake catalog: `orchestration/dev_employee_intake_catalog/`
- task runs: `orchestration/task_runs/`
- intentional evidence: `logs/dev_employee/`
- durable context: `memory/dev_employee/` and `docs/`

Raw chat sessions, locks, raw Harness traces, transient plans and high-volume runtime noise must remain local and ignored.

GitHub is the durable boundary for source, decisions, commits, remote SHA and intentional evidence. It is not the high-frequency runtime database.

Separate insight/research storage remains PostgreSQL:

- database: `oris_insight`
- schema: `insight`
- config: `config/insight_storage.json`
- bootstrap: `sql/insight_schema_v1.sql`

Do not couple Dev Employee runtime to the insight schema without an explicit architecture decision.

## Executor and provider truth

### Codex

The previous `refresh_token_reused` blocker is resolved.

Verified:

- admin login;
- non-interactive `codex exec`;
- systemd bridge authentication context;
- pre-execution auth preflight;
- terminal auth failure before product mutation.

Old documentation saying Codex authentication is currently invalid is historical.

### OpenClaw and Harness

- OpenClaw is an existing active installation;
- the custom shell used OpenClaw only as a provider/inference backend;
- the commercial target uses native OpenClaw UI and native session semantics;
- ORIS must be exposed as stable tools/actions/plugins, not broad prompt-keyword matching;
- Agent Harness remains a backend structured-output, policy and fallback layer.

Provider availability, model ids, quota and price are runtime facts and must be probed when needed. ZenMux remains excluded unless explicitly reopened.

## Secret boundaries

Secret values remain local-only, including OpenClaw credentials, Codex auth state, service environment files, project `.env` files, Nginx auth data, TLS private keys and provider/product credentials.

Never print or commit secret values. Record only presence, validation status and non-secret identity/context. Never include secrets in chat or `===== SUMMARY =====`.

## Interaction workflow

- use Chinese, professional and direct;
- do not ask the user to choose routine engineering details;
- write long scripts/docs/patches directly to GitHub;
- give one short command to fetch and run the GitHub script;
- do not rely on long terminal heredocs because they may be truncated;
- write detailed logs only as intentional evidence;
- inspect logs from GitHub instead of asking the user to paste them;
- every user-run script ends with one concise SUMMARY block;
- user sends only the SUMMARY block;
- user-facing Linux scripts must not use `set -e`.

## Operational lessons

- never patch an ignored duplicate Nginx virtual host;
- do not append to a tracked log after committing it;
- use a detached worktree for evidence when the main worktree contains an intentional patch;
- set the runtime `PYTHONPATH` explicitly when service modules depend on `scripts/`;
- do not assume system Python includes pytest;
- verify every requested deliverable, not only UI status or model text.
