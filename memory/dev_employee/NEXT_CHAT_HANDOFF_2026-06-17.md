# ORIS / OpenClaw / Codex-backed AI Dev Employee — Next Chat Handoff

Date: 2026-06-17

## Mandatory read order

1. `memory/dev_employee/CONTEXT_INDEX.md`
2. `memory/dev_employee/CURRENT_STATE_2026-06-17.md`
3. `memory/dev_employee/SESSION_ARCHIVE_2026-06-17.md`
4. `memory/dev_employee/current_task.json`
5. `memory/dev_employee/current_task.md`
6. `docs/DEV_EMPLOYEE_NATIVE_OPENCLAW_UI_DECISION_2026-06-17.md`
7. `docs/DEV_EMPLOYEE_NATIVE_OPENCLAW_UI_MIGRATION_PLAN_2026-06-17.md`
8. `docs/DEV_EMPLOYEE_ENVIRONMENT_ADDENDUM_2026-06-17.md`
9. `docs/DEV_EMPLOYEE_ENGINEERING_STANDARD_2026-06-16.md`
10. `docs/DEV_EMPLOYEE_ENGINEERING_STANDARD_ADDENDUM_2026-06-17.md`
11. `docs/DEV_EMPLOYEE_QUEUE_LIFECYCLE_HARDENING_2026-06-16.md`
12. `memory/dev_employee/FINAL_ACCEPTANCE_COMPLETION_2026-06-16.md`
13. `orchestration/project_registry.json`
14. `memory/dev_employee/NEW_CHAT_BOOTSTRAP_PROMPT_2026-06-17.md`

Do not reconstruct the project from chat history when these files exist.

## Current objective

Make the existing native OpenClaw Gateway UI the primary experience at `https://control.orisfy.com`.

Target chain:

```text
human -> native OpenClaw UI -> Agent Harness tool/policy adapter
      -> ORIS intake/lifecycle/queue -> Codex -> product/evidence
```

Do not continue productizing the custom ORIS Web Console v5 chat shell.

## User decision

The custom shell was rejected because it is not the native OpenClaw interface and lacks:

- new conversation;
- visible history/sidebar;
- session switching;
- clear/archive/delete;
- native prompt semantics.

Old failures remained mixed in one long-lived session and custom intent routing required special rules.

Decision:

- native OpenClaw UI is primary;
- Harness remains backend-only;
- ORIS is exposed through stable tools/actions;
- custom shell becomes a restricted diagnostic/rollback route;
- do not reinstall or upgrade OpenClaw during migration.

## Current platform state

Working:

- public-Web-to-Codex-to-GitHub final acceptance;
- Codex auth and bridge-context preflight;
- canonical terminal states;
- queue kernel with atomic claim, lease, heartbeat, timeout, cancel, retry and concurrency;
- intake v2 and bridge v3;
- GitHub evidence and remote-SHA verification;
- existing OpenClaw Gateway discovered and active;
- Agent Harness backend integrated;
- public chat POST and intent-boundary defects repaired.

Services at handoff:

- `openclaw-gateway.service`: active, `127.0.0.1:18789`
- `oris-dev-employee-web-console.service`: active, `127.0.0.1:18893`
- `oris-dev-employee-intake.service`: active, `127.0.0.1:18892`
- `oris-dev-employee-bridge.service`: active

Current public root still points to the custom shell.

## First action in the new chat

Do not change Nginx and do not submit another product task immediately.

Create a GitHub-hosted read-only discovery script for:

1. OpenClaw systemd unit, process and listener;
2. native UI root/static routes;
3. WebSocket route and upgrade requirements;
4. auth/token/device-pairing behavior without exposing values;
5. native history/new-conversation/switch/clear capabilities;
6. effective `control.orisfy.com` Nginx load order and server block;
7. current root, `/admin` and OpenClaw proxy routes;
8. duplicate/ignored Nginx server blocks;
9. service health and absence of active tasks;
10. product baseline and clean state.

The script is read-only, commits sanitized evidence, submits no task and ends with `===== SUMMARY =====`.

After reading the evidence, build a reversible route-switch script.

## Migration target

- `/` -> native OpenClaw Gateway on port 18789
- native OpenClaw static/WebSocket/API routes -> port 18789
- `/admin` -> restricted ORIS console on port 18893
- non-default rollback route -> custom shell on port 18893
- intake port 18892 remains private

Do not assume OpenClaw supports a path prefix until discovery proves it.

## OpenClaw-to-ORIS rule

Do not use broad keyword matching inside user prompts.

Use stable tools/actions for:

- list projects;
- create goal;
- get status/evidence;
- cancel;
- retry;
- confirm genuinely risky operations.

Natural-language development goals must not require ORIS-specific syntax.

## Controlled task gap

Task:

`chat-oris-final-acceptance-api-20260617-051313-c802347ff17c`

Product commit:

`927f1968cc86bfd5213670f4eaa171fc1a3be620`

Completed: `/capabilities` and tests.

Missing: requested README API-list update.

Treat it as partially delivered. Repair README after native UI acceptance, then verify tests, product remote SHA and ORIS evidence.

## Environment anchors

- ORIS host: `43.106.55.255`
- user: `admin`
- ORIS path: `/home/admin/projects/oris`
- product path: `/home/admin/projects/oris-final-acceptance-api`
- public entry: `https://control.orisfy.com`
- production host: `8.136.28.6`, user `deploy`; do not touch

## Interaction and engineering rules

- Chinese, professional, direct and structured;
- do not ask the user to decide routine engineering details;
- write long scripts/docs directly to GitHub;
- give one short command to fetch/run the GitHub file;
- avoid long terminal heredocs because they may be truncated;
- user sends only the SUMMARY block;
- read complete logs from GitHub;
- never print secrets;
- no `set -e` in user-facing scripts;
- back up, validate, reload, and roll back safely;
- use detached worktrees for evidence when needed;
- do not append to tracked logs after commit;
- layered and decoupled;
- configuration/secrets/runtime separation;
- one rule, one authoritative source;
- `main` is the only mainstream branch;
- ORIS owns platform/evidence; product repos own product code/docs/tests;
- build generic commercial mechanisms;
- completion requires every requested deliverable, tests, product SHA, remote SHA and ORIS evidence.

## Next milestone acceptance

The milestone passes only when native OpenClaw is at the public root, WebSocket/auth work, `/admin` and rollback route remain available, intake stays private, browser new-conversation/history/switch/clear behavior is verified, no product repository changes occur, and migration/rollback evidence is committed.
