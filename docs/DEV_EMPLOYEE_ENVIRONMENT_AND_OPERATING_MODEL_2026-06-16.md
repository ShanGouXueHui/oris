# ORIS Dev Employee Environment and Operating Model — 2026-06-16

## 1. Environment map

### ORIS development and execution host

- public IP: `43.106.55.255`
- logical role: Singapore development/execution machine
- Linux user: `admin`
- ORIS path: `/home/admin/projects/oris`
- projects root: `/home/admin/projects`
- Codex install root: `/home/admin/.npm-global/`
- Codex executable used by queue descriptors: `/home/admin/.npm-global/lib/node_modules/@openai/codex/bin/codex.js`
- GitHub identity: `ShanGouXueHui`
- Git transport: SSH

This host is the current ORIS Dev Employee control and code-execution environment.

### Separate production host

- public IP: `8.136.28.6`
- logical role: Hangzhou production machine
- Linux user: `deploy`

This production host is used for other product workloads such as AIdeal CPS. It is not automatically an ORIS Dev Employee execution target. Any production action requires an explicit project/deployment task and the applicable approval boundary.

## 2. Public domains and networking

Official domain base:

- `orisfy.com`

Current Dev Employee public control entry:

- `https://control.orisfy.com`

DNS:

- `control.orisfy.com` resolves to `43.106.55.255`.

Nginx responsibilities:

- HTTPS termination using Let's Encrypt/Certbot-managed certificate paths;
- Basic Auth;
- exact path/method restrictions;
- reverse proxy only to the local Web Console;
- no direct public proxy to intake.

## 3. Local service topology

### Dev Employee Web Console

- bind: `127.0.0.1:18893`
- service: `oris-dev-employee-web-console.service`
- function: public-facing UI backend, token gate, project filter, submit/status adapter

### Dev Employee intake/status API

- bind: `127.0.0.1:18892`
- service: `oris-dev-employee-intake.service`
- function: validate goals, build prompt/descriptor, persist catalog, enqueue, expose status

### Dev Employee supervised bridge

- service: `oris-dev-employee-bridge.service`
- function: claim queue items, run Codex, validate results, commit/push product changes, persist ORIS evidence

### OpenClaw gateway baseline

- bind: `127.0.0.1:18789`
- service: `openclaw-gateway.service`
- role: channel/access/plugin gateway

The OpenClaw baseline is part of ORIS vNext architecture, but the current public Dev Employee Web Console is a separate local service behind Nginx.

### ORIS Free Mesh historical baseline

- OpenAI-compatible local endpoint previously documented at `127.0.0.1:8789/v1`
- model id: `oris/free-auto`

Treat this as a historical validated baseline unless a current health probe confirms it. It is not the executor for the current failed coding task.

## 4. Repositories and paths

### Platform

- repo: `ShanGouXueHui/oris`
- local: `/home/admin/projects/oris`
- branch: `main`

### Current acceptance product

- repo: `ShanGouXueHui/oris-final-acceptance-api`
- local: `/home/admin/projects/oris-final-acceptance-api`
- branch: `main`

### Other registered projects

Current registry includes:

- `oris`
- `aideal-cps`
- `aideal-site`
- `kindafeelfy-nolly`
- `oris-dev-smoke-app`
- `oris-final-acceptance-api`

A project being in the registry does not automatically mean it is enabled in the public Web Console allowlist.

## 5. Database and durable storage

### Dev Employee task state

Current implementation uses filesystem/GitHub-backed artifacts:

- queue descriptors under `orchestration/dev_employee_queue/`;
- task catalog under `orchestration/dev_employee_intake_catalog/`;
- task runs under `orchestration/task_runs/`;
- progress/evidence under `logs/dev_employee/`;
- long-term context under `memory/dev_employee/` and `docs/`.

GitHub is the durable delivery/evidence boundary.

Commercial target:

- transaction-safe task/event database for runtime state;
- GitHub remains the code/delivery/evidence record.

### Insight platform database

Separate ORIS insight/research workloads use PostgreSQL:

- database: `oris_insight`
- schema: `insight`
- non-secret config: `config/insight_storage.json`
- schema bootstrap: `sql/insight_schema_v1.sql`

Do not couple Dev Employee task execution directly to the insight schema without an explicit architecture change.

## 6. Models and providers

### Coding executor

- primary real coding executor: Codex CLI
- recorded version: `codex-cli 0.133.0`
- provider in latest failed log: OpenAI
- model in latest failed log: `gpt-5.5`
- sandbox: `workspace-write`
- approval mode: `never`

Current auth state:

- invalid;
- refresh failed with HTTP 401 and `refresh_token_reused`;
- requires logout/sign-in and same-context verification.

### General model fabric

ORIS provider orchestration supports or has historically integrated candidates including:

- OpenRouter;
- Gemini;
- Zhipu;
- Ali Bailian;
- Tencent Hunyuan;
- NVIDIA hosted endpoints;
- Hugging Face.

Provider availability, free quota, and model names are runtime facts. They must be probed and must not be treated as permanent documentation facts.

ZenMux is excluded from provider recommendations unless explicitly reopened by the user.

## 7. Secret and local configuration locations

Known local-only stores include:

- `~/.openclaw/secrets.json`
- `~/.openclaw/agents/main/agent/auth-profiles.json`
- `~/.config/oris/dev_employee_enqueue.env`
- project-local `.env` files where applicable
- host-managed Nginx htpasswd and TLS private-key paths
- Codex local authentication state

Rules:

- never commit these values;
- never print them in GitHub logs;
- never include them in `===== SUMMARY =====`;
- print only presence/absence and validation status;
- rotate credentials after accidental exposure.

## 8. Public Web security model

Current persistent mode:

- Basic Auth at Nginx;
- Console Token at Web Console API;
- allowlist restricted to `oris-final-acceptance-api`;
- only exact `/api/goals` POST opened;
- intake not exposed;
- audit logs sanitized.

The public control plane is intended to remain persistently usable, not a temporary test window.

## 9. User interaction and execution workflow

### Preferred interaction

- Chinese;
- professional, direct, structured;
- data/evidence driven;
- no unnecessary praise or emotional filler;
- do not ask the user to decide routine technical steps.

### GitHub-first workflow

For substantial changes:

1. assistant reads current GitHub context;
2. assistant directly creates/updates scripts/docs in GitHub;
3. user runs one short copy-paste command to fetch/reset and execute the GitHub script;
4. script writes useful logs under `logs/dev_employee/`;
5. script commits/pushes the log when appropriate;
6. user sends only the final SUMMARY block;
7. assistant reads full logs from GitHub.

Do not ask the user to paste long logs that are already available in GitHub.

### Script output contract

Every operational script intended for the user must end with:

```text
===== SUMMARY =====
RESULT=...
...
SEND_TO_CHAT=THIS_SUMMARY_ONLY
===== END SUMMARY =====
```

The SUMMARY must contain only concise non-secret facts needed for the next decision.

### Shell constraints

- do not use `set -e` in user-facing scripts;
- use explicit `|| exit 1` only for truly mandatory boundaries;
- keep scripts idempotent or safely repeatable;
- back up host config before mutation;
- run syntax/preflight checks before reload/restart;
- write verbose output to log files;
- keep terminal output decision-oriented.

## 10. Source-of-truth and logging rules

Commit:

- code/config/docs changes;
- acceptance evidence;
- decision-useful diagnostic summaries;
- task evidence required for audit.

Do not commit by default:

- tokens or credentials;
- `.env`;
- caches/venvs;
- raw high-volume runtime noise;
- transient locks and pid files;
- unrelated historical untracked logs.

The current repository contains substantial historical untracked runtime noise on the server. Commercial hardening should cleanly separate ignored runtime storage from intentional evidence without deleting historical evidence blindly.
