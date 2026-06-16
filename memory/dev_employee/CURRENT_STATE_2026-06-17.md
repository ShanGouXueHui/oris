# ORIS / OpenClaw / Codex-backed AI Dev Employee — Current State

Date: 2026-06-17

## 1. Executive status

ORIS Dev Employee has a working, audited public-Web-to-Codex-to-GitHub delivery chain and has moved into commercial productization.

The execution/control plane is materially functional:

- public HTTPS entry;
- authenticated project access;
- intake/status control plane;
- transaction-safe filesystem queue kernel;
- lease, heartbeat, timeout, cancel and explicit retry;
- supervised Codex bridge;
- Codex authentication preflight;
- product testing, commit, push and remote-SHA verification;
- ORIS evidence and lifecycle status;
- OpenClaw Gateway available as the model/channel runtime.

The immediate blocker is no longer executor reliability. It is the primary user experience and integration boundary.

The custom `ORIS AI 开发员工` Web Console v5 was useful for proving the chain, but the operator rejected it as the commercial primary UI because it is not the native OpenClaw interface and lacks standard conversation lifecycle capabilities.

Current phase:

> Restore the existing native OpenClaw Gateway UI as the primary public experience, expose ORIS through stable tools/actions, retain Agent Harness as a backend policy adapter, and keep the custom shell only as a temporary diagnostic/rollback surface.

## 2. Authoritative architecture decision

Target chain:

```text
human
  -> native OpenClaw UI and native conversation/session model
  -> Agent Harness tool/policy adapter
  -> ORIS control plane
  -> Codex CLI executor
  -> product repository + tests + commit/push
  -> ORIS evidence/status returned to OpenClaw
```

Responsibility boundaries:

- **Native OpenClaw UI**: normal chat behavior, new conversation, history, switching, clearing/archiving, channel access and native session semantics.
- **Agent Harness**: backend structured tool contract, risk/policy validation, provider-neutral routing and fallback. It must not own the main UI or force users to write ORIS-specific prompts.
- **ORIS**: project registry, authorization policy, intake, task identity, lifecycle, queue, leases, cancellation, retry, evidence and audit.
- **Codex**: real implementation, tests, repair, commit and controlled push.
- **Custom ORIS Web Console v5**: no longer a product UX target; retain temporarily only under a non-default diagnostic/rollback route.

Do not reinstall or upgrade OpenClaw as part of the UI migration.

## 3. Environment and service topology

### ORIS development/execution host

- host: `43.106.55.255`
- Linux user: `admin`
- project root: `/home/admin/projects`
- ORIS repo: `/home/admin/projects/oris`
- public domain: `https://control.orisfy.com`
- GitHub owner: `ShanGouXueHui`
- mainstream branch: `main`

### Separate production host

- host: `8.136.28.6`
- Linux user: `deploy`
- role: production workloads outside this migration
- rule: do not touch without an explicit production/deployment task

### Current local services

- OpenClaw Gateway: `openclaw-gateway.service`, historical/current loopback port `127.0.0.1:18789`
- custom Web Console v5: `oris-dev-employee-web-console.service`, `127.0.0.1:18893`
- intake/status API v2: `oris-dev-employee-intake.service`, `127.0.0.1:18892`
- supervised bridge v3: `oris-dev-employee-bridge.service`

All four services were active at the end of the conversation.

### Current public route

`control.orisfy.com` currently serves the custom ORIS Web Console v5 through Nginx. The next migration must switch the root route to the native OpenClaw Gateway UI, preserve WebSocket/token/device-pairing behavior, retain `/admin`, and provide an explicit rollback route to the custom shell.

## 4. Storage, databases and durable records

### Dev Employee operational state

The current commercial kernel remains filesystem-backed but transaction-hardened:

- queue descriptors: `orchestration/dev_employee_queue/`
- intake catalog: `orchestration/dev_employee_intake_catalog/`
- task run/evidence results: `orchestration/task_runs/`
- intentional audit/evidence: `logs/dev_employee/`
- durable architecture and handoff memory: `memory/dev_employee/` and `docs/`

Runtime chat sessions, locks, transient plans and raw traces are local runtime state and must remain ignored/untracked. GitHub is the durable code, decision and acceptance-evidence boundary, not a high-frequency runtime database.

### Separate insight database

Research/insight workloads use PostgreSQL:

- database: `oris_insight`
- schema: `insight`
- non-secret config: `config/insight_storage.json`
- bootstrap: `sql/insight_schema_v1.sql`

Do not couple Dev Employee task execution to the insight schema without an explicit architecture decision.

## 5. Models, providers and executor

### Coding executor

- real coding executor: Codex CLI
- execution identity: Linux user `admin`
- bridge and interactive admin context were verified to use the same authentication context
- non-interactive Codex execution preflight: passed
- systemd bridge-context preflight: passed
- auth preflight runs before real execution
- authentication failures are terminal preflight failures and must not mutate a product repository

The previous `refresh_token_reused` blocker is resolved. Old documents describing Codex authentication as invalid are historical only.

### OpenClaw and Agent Harness

- OpenClaw was discovered as an existing installation and was not reinstalled or upgraded.
- The custom shell used OpenClaw as a provider/inference backend, not as its native UI.
- Agent Harness v1 was added as a provider-neutral backend contract/policy layer.
- For the commercial target, OpenClaw native conversation behavior must remain primary and ORIS must be exposed through tools/actions rather than prompt keyword interception.

Provider/model availability is a runtime fact and must be probed. Do not hardcode volatile provider availability or quota assumptions in architecture documents.

ZenMux remains excluded unless explicitly reopened by the user.

## 6. Completed milestones

### 6.1 Full-chain final acceptance

Task:

`goal-oris-final-acceptance-api-readonly-e2e-20260616-044030`

Result: `completed`

Verified chain:

`public Web -> Basic Auth -> project allowlist -> intake -> queue -> bridge -> Codex -> product checks -> product commit/push -> remote SHA -> ORIS evidence/index`

Key evidence:

- product commit/remote SHA: `3207f20a2afdf109beac9a4a95523e7792e0ae33`
- ORIS evidence commit: `188a17eeba4acb43f5b922560ad98c3d8d28c587`
- ORIS evidence index commit: `4425edbe8e29912ff44d41da2a5e458bdac292d3`
- independent verification log commit: `f1bb1cfcefbd7a3b5abb2a4f3bf6b4c00707605e`

Do not rerun this exact acceptance task without regression evidence.

### 6.2 Queue and lifecycle hardening

P1-A was deployed and accepted:

- atomic claim and per-task locking;
- canonical lifecycle states and terminal-state handling;
- leases, heartbeat and execution deadline;
- explicit cancellation and rollback before delivery;
- explicit bounded retry with new Task ID/lineage;
- concurrency slot enforcement;
- append-only lifecycle events;
- stale-task recovery without automatic duplicate execution;
- bridge v3 and intake v2 active;
- browser lifecycle controls validated.

### 6.3 Codex authentication hardening

Completed:

- admin device-code login;
- non-interactive `codex exec` verification;
- systemd bridge auth-context verification;
- Codex auth preflight;
- `codex_failed` and related failures normalized as terminal states;
- polling stops on terminal failure;
- no real task submitted until auth preflight passed.

### 6.4 Conversation-chain technical validation

Completed:

- existing OpenClaw runtime discovery;
- OpenClaw provider probe;
- Agent Harness integration;
- public chat POST Nginx repair;
- CSRF and Basic Auth preserved;
- other public engineering POST routes remained blocked;
- custom conversation shell server smoke passed;
- status-code intent collision fixed;
- negative secret constraint such as `不要修改任何密钥` no longer classified as a secret operation;
- relevant unittest and exact-message regression passed.

## 7. Controlled browser task completed with an acceptance gap

Task ID:

`chat-oris-final-acceptance-api-20260617-051313-c802347ff17c`

Product commit:

`927f1968cc86bfd5213670f4eaa171fc1a3be620`

Implemented:

- `GET /capabilities`;
- response fields `service`, `storage`, `features`;
- features include `task_crud`, `filtering`, `stats`;
- tests for status code and response contract.

Acceptance gap:

- the operator explicitly required the README API list to be updated;
- `README.md` was not changed in the product commit.

Therefore the task is functionally completed but not fully requirement-compliant. Do not label it final acceptance PASS until README is repaired and tests/product remote SHA/ORIS evidence are re-verified.

## 8. Why the custom shell was rejected

The page titled `ORIS AI 开发员工` was developed in the ORIS repository. It is not the OpenClaw native interface.

Observed issues:

- no new-conversation action;
- no conversation-history sidebar;
- no conversation switching;
- no clear/archive/delete lifecycle;
- one long-lived HttpOnly cookie silently reuses a single server-side session;
- previous failures remain mixed with later work;
- custom keyword/intent routing alters normal prompt semantics;
- task cards are repeatedly appended to the transcript;
- the user must learn ORIS-specific commands and prompt constraints.

Decision: do not spend the next phase rebuilding native OpenClaw functions in this shell.

## 9. Current blockers and risks

### P0 — native OpenClaw UI migration

Before changing Nginx, read-only discover:

- active OpenClaw process/service and exact executable/config;
- native HTTP routes and static assets;
- WebSocket route and upgrade headers;
- authentication/token/device-pairing behavior;
- native conversation/session/history persistence;
- whether the current native UI supports new conversation, history switching and clearing/archiving in the installed version;
- effective Nginx server block and duplicate-server-name risks;
- safe rollback route for custom Web Console v5.

### P0 — tool integration correctness

The native UI must invoke ORIS through a stable tool/action/plugin contract. Do not implement task creation through broad keyword matching in user prompts.

The integration must support:

- list allowed projects;
- create goal;
- get status/evidence;
- cancel;
- explicit retry;
- human confirmation for genuinely risky operations;
- structured errors and terminal states.

### P0 — repair incomplete controlled task

After native UI browser acceptance, repair the missing README update in `oris-final-acceptance-api`, run product checks, commit/push, verify remote SHA and update ORIS evidence.

### P1 — commercial security and operations

- SSO/OIDC and RBAC;
- tenant/user/project isolation;
- audit retention/privacy policy;
- rate limiting and abuse controls;
- monitoring, metrics, alerts and SLOs;
- backup/restore and disaster recovery;
- upgrade/rollback automation;
- generic project onboarding;
- eventual database-backed task/event store.

## 10. Known operational lessons

1. Do not modify a duplicate/ignored Nginx virtual host. Use `nginx -T` and patch the first effective server block.
2. Public method policy must allow only the exact required write route; preserve all other read-only guards.
3. Do not assume system Python contains pytest. Use the project runtime or standard-library unittest when tests are unittest-based.
4. For test imports matching service runtime, set the correct `PYTHONPATH` explicitly.
5. Do not write a tracked log, commit it, and then append more output to the same file. This creates immediate worktree drift.
6. Submit evidence through a detached worktree when the main worktree contains an intentional patch or when logging would dirty tracked files.
7. Runtime state and raw chat history must remain outside Git.
8. A UI `completed` label is insufficient; verify every requested deliverable, tests, changed-file scope, product SHA, remote SHA and ORIS evidence.
9. Keep only one mainstream branch (`main`). Backups may be private archives, files, tags, commits or short-lived branches, but not competing long-lived branches.
10. Never put product code in ORIS or ORIS platform code in a product repository.

## 11. User interaction contract

- communicate in Chinese;
- professional, direct and structured;
- do not ask the user to decide routine engineering details;
- directly update long scripts, docs and patches in GitHub;
- give the user one short command to fetch and run a GitHub-hosted script;
- write verbose logs under `logs/dev_employee/` only when they are intentional evidence;
- read full logs from GitHub rather than asking the user to paste them;
- every user-run operational script ends with `===== SUMMARY =====`;
- the user sends only the SUMMARY block;
- never output tokens, passwords, private keys or secret values in chat, SUMMARY or GitHub;
- do not use `set -e` in user-facing Linux scripts;
- scripts must back up before mutation, validate before reload/restart, and roll back on failure;
- long documents must be committed directly to GitHub because long terminal commands may be truncated.

## 12. Immediate next action

Do not submit another product task yet.

1. run read-only discovery of the existing native OpenClaw UI and effective Nginx routing;
2. persist a sanitized discovery report in GitHub;
3. design a reversible migration:
   - native OpenClaw at `/`;
   - custom shell at a restricted rollback/diagnostic route;
   - `/admin` preserved;
   - WebSocket and native auth preserved;
4. server-test the migration without reinstalling OpenClaw;
5. ask the operator to browser-test native new conversation, history, switching and clear/archive;
6. expose ORIS as native OpenClaw tools/actions;
7. browser-test a normal natural-language development goal;
8. repair the missing README update and complete evidence verification.
