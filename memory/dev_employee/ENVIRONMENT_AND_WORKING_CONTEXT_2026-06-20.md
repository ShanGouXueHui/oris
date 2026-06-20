# ORIS Dev Employee Environment and Working Context Snapshot — 2026-06-20

## 1. Scope

This file is the current environment, surrounding-system, runtime-boundary and interaction snapshot for new ORIS commercialization conversations.

It supersedes earlier mutable statements that describe the runtime as tools-denied or read-only acceptance as unresolved.

Historical evidence remains unchanged.

## 2. Hosts

### Development/control/execution

- host: `43.106.55.255`;
- user: `admin`;
- projects root: `/home/admin/projects`;
- ORIS repository: `/home/admin/projects/oris`;
- GitHub repository: `ShanGouXueHui/oris`;
- only mainstream branch: `main`.

### Production

- host: `8.136.28.6`;
- user: `deploy`;
- rule: do not touch unless a separate explicit production task is created.

Development and production responsibilities must never be silently mixed.

## 3. Public and local services

Public:

- `https://control.orisfy.com`;
- `/`: native OpenClaw UI and session system;
- `/admin`: restricted ORIS administration and diagnostics;
- `/_oris-chat-shell`: restricted rollback and diagnostics.

Local:

- OpenClaw Gateway: `openclaw-gateway.service`, `127.0.0.1:18789`;
- Free Mesh API: `oris-free-mesh-api.service`, loopback port `8789`;
- ORIS enqueue/status: `127.0.0.1:18891`;
- ORIS intake: `127.0.0.1:18892`;
- ORIS Web Console: `127.0.0.1:18893`;
- supervised bridge: `oris-dev-employee-bridge.service`.

Ports `18891` and `18892` must remain loopback-only and must not be exposed through Nginx.

## 4. Runtime and model stack

- OpenClaw: `2026.5.19 (a185ca2)`;
- Node: `v22.22.2`;
- npm: `10.9.7`;
- Codex CLI: real coding executor;
- OpenClaw controls the conversation provider/model path;
- Provider/model identity, quota, capability, latency and cost are runtime facts;
- shared code must not hardcode provider or model identity;
- ZenMux remains excluded unless explicitly reopened.

The accepted read-only evidence observed bounded runtime identifiers `provider=oris` and `model=free-auto`. They are one-run runtime facts, not stable configuration authority.

## 5. Plugin, Skill and tool state

Plugin:

- id: `oris-dev-employee`;
- version: `0.1.0`;
- source commit: `8f174b49196aac90b505846200ce260f75355b41`;
- original installation result: `INSTALLED_TOOLS_DENIED`;
- current read-only policy: enabled and accepted.

Accepted read-only ORIS tools:

- `oris_queue_status`;
- `oris_task_status`;
- `oris_latest_task_status`.

Typed hooks:

- `model_call_ended`;
- `after_tool_call`;
- `agent_end`.

Routing Skill:

- name: `oris-readonly-status`;
- installed: yes;
- selected Agent: `main`;
- runtime-visible: yes.

Current policy mode:

`profile-authority-preserved+created-profile-also-allow+skill-unrestricted`

Native support-tool contract:

- `read` may occur at most once;
- it must precede the first ORIS business-tool call;
- it must succeed;
- it is Skill hydration support, not an ORIS business tool.

Write state:

- no generic `exec` tool authorized;
- no generic file-write tool authorized;
- no typed write action registered or enabled;
- no real product write acceptance authorized.

## 6. Read-only P0 evidence

Evidence commit:

`65217d4bb81f4ac3cd8c6d917af95425d2b47529`

Result:

`ENABLED_READONLY_AUTOMATIC_ACCEPTED`

Checks:

- 26 total;
- 26 pass;
- 0 fail;
- 0 not checked.

Retained runtime:

- read-only policy retained;
- Routing Skill retained;
- private marker retained;
- rollback count 0;
- Gateway healthy;
- queue unchanged;
- product unchanged;
- write tools absent;
- no product task submitted.

## 7. Repositories and ownership

### ORIS platform

Owns:

- platform orchestration;
- task lifecycle;
- authorization and policy;
- queue and attempt state;
- OpenClaw/Plugin/Harness adapters;
- evidence and durable context.

### Product repositories

Own:

- product source;
- product tests;
- product documentation;
- product commits and delivery artifacts.

Final acceptance product:

- repository: `ShanGouXueHui/oris-final-acceptance-api`;
- local path: `/home/admin/projects/oris-final-acceptance-api`;
- verified baseline: `bcb93e17ea88704548101f5e4a5c460e15a80ec7`.

Do not move or duplicate product implementation into ORIS.

Project boundaries are governed by `orchestration/project_registry.json`.

## 8. Operational state and database

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
- security result: `ALREADY_SECURE_AND_VERIFIED`;
- evidence: `bc799a640138a19800270ecab1a656f09d70252a`.

Do not move Dev Employee queue/task truth into PostgreSQL without a separate architecture decision and migration plan.

## 9. Initial latency baseline

Source:

`docs/DEV_EMPLOYEE_READONLY_P0_COMPLETION_AND_LATENCY_BASELINE_2026-06-20.md`

Observed baseline v1:

- model: count 8, min 2,661 ms, P50 5,478 ms, max 49,734 ms;
- Agent total: count 3, min 8,538 ms, P50 9,029 ms, max 69,134 ms;
- ORIS queue tool: 13 ms;
- ORIS task tool: 42 ms;
- ORIS latest-task tool: 13–41 ms, P50 27 ms;
- Skill hydration `read`: 92 ms.

TTFT is unavailable from the approved typed hooks.

This is not yet an SLO or SLA.

## 10. Secret and privacy boundary

Local-only secrets include:

- OpenClaw auth state;
- Codex auth;
- service environment files;
- product `.env`;
- Nginx auth;
- TLS keys;
- database/provider credentials;
- private plugin markers;
- secret-bearing backups.

Allowed evidence:

- presence or validation status;
- bounded counts;
- non-secret mode names;
- hashes;
- bounded provider/model runtime identifiers where explicitly permitted;
- privacy-safe aggregate durations.

Forbidden evidence:

- raw config;
- token/password/key values;
- prompts or messages;
- assistant responses;
- tool arguments or tool results;
- headers, cookies or auth state;
- raw private marker content;
- raw session identifiers;
- hidden model reasoning;
- unbounded service journals.

## 11. Interaction preferences

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

## 12. Engineering preferences

- inspect before editing;
- run a fresh code-first audit on current `main` before the next source phase;
- remove duplicate functions, variables, classes, parsers, policies and helpers before feature work;
- one rule has one authoritative implementation;
- no competing authority;
- no duplicate function bodies;
- no import cycles;
- configuration and code remain separated;
- large files are split by responsibility;
- shared code does not hardcode project/path/host/port/branch/provider/model/runtime/version or acceptance special cases;
- changes are generic commercial implementations;
- temporary backups, short-lived branches and detached worktrees are allowed;
- no competing long-lived branches;
- completed work requires real tests, commit SHA, remote SHA and sanitized evidence;
- do not append to tracked evidence logs after commit.

## 13. Current continuation boundary

Read-only P0 is complete.

The next phase is controlled typed write-action design and offline implementation foundation.

Authoritative plan:

`docs/DEV_EMPLOYEE_TYPED_WRITE_ACTIONS_COMMERCIAL_PHASE_PLAN_2026-06-20.md`

The next conversation must:

- audit current `main` first;
- inspect existing authorization/task/queue/idempotency/Plugin/Harness authorities;
- avoid duplicate implementation;
- keep the accepted read-only policy unchanged;
- keep write actions unregistered and runtime-disabled;
- submit no real product task during contract-only design;
- touch no production system.
