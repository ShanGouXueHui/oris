# ORIS Dev Employee — Authoritative Context Index

Last updated: 2026-06-17

## Purpose

This is the stable entry point for every new ORIS / OpenClaw / Codex-backed AI Dev Employee conversation.

Do not reconstruct the project from chat history when these GitHub files are available.

## Mandatory read order

1. `memory/dev_employee/CURRENT_STATE_2026-06-17.md`
2. `memory/dev_employee/current_task.json`
3. `memory/dev_employee/current_task.md`
4. `docs/DEV_EMPLOYEE_NATIVE_OPENCLAW_UI_DECISION_2026-06-17.md`
5. `docs/DEV_EMPLOYEE_NATIVE_OPENCLAW_UI_MIGRATION_PLAN_2026-06-17.md`
6. `docs/DEV_EMPLOYEE_ENVIRONMENT_ADDENDUM_2026-06-17.md`
7. `docs/DEV_EMPLOYEE_ENGINEERING_STANDARD_2026-06-16.md`
8. `docs/DEV_EMPLOYEE_ENGINEERING_STANDARD_ADDENDUM_2026-06-17.md`
9. `docs/DEV_EMPLOYEE_QUEUE_LIFECYCLE_HARDENING_2026-06-16.md`
10. `memory/dev_employee/FINAL_ACCEPTANCE_COMPLETION_2026-06-16.md`
11. `docs/DEV_EMPLOYEE_COMMERCIAL_ARCHITECTURE_2026-06-16.md`
12. `docs/DEV_EMPLOYEE_AUTONOMOUS_EXECUTION_POLICY_ADDENDUM_2026-06-16.md`
13. `docs/DEV_EMPLOYEE_AUTONOMOUS_EXECUTION_POLICY.md`
14. `orchestration/project_registry.json`
15. `memory/dev_employee/NEXT_CHAT_HANDOFF_2026-06-17.md`
16. `memory/dev_employee/NEW_CHAT_BOOTSTRAP_PROMPT_2026-06-17.md`

## Authority hierarchy

When documents conflict, use this order:

1. latest dated file under `memory/dev_employee/`;
2. `memory/dev_employee/current_task.json`;
3. latest 2026-06-17 architecture/decision/addendum documents;
4. current machine-readable configuration and project registry;
5. latest task/evidence under `orchestration/task_runs/` and `logs/dev_employee/`;
6. older dated state, handoff and architecture documents.

Historical evidence must not be rewritten to conceal what happened. Correct current truth with a newer authoritative document or an explicit superseding addendum.

## Current product decision

The custom `ORIS AI 开发员工` Web Console v5 is not the native OpenClaw interface and is rejected as the commercial primary UI.

Approved target:

```text
human -> native OpenClaw UI -> Agent Harness tool/policy adapter
      -> ORIS control plane -> Codex -> product/evidence
```

Rules:

- do not reinstall or upgrade OpenClaw during migration;
- reuse the active OpenClaw Gateway on loopback port 18789;
- Agent Harness remains a backend component, not the main UI;
- expose ORIS through stable tools/actions, not broad prompt keyword matching;
- preserve `/admin` and a restricted custom-shell rollback route;
- keep intake private.

## Completed prerequisites

### Full-chain final acceptance

- task: `goal-oris-final-acceptance-api-readonly-e2e-20260616-044030`
- canonical status: `completed`
- product commit/remote SHA: `3207f20a2afdf109beac9a4a95523e7792e0ae33`
- ORIS evidence commit: `188a17eeba4acb43f5b922560ad98c3d8d28c587`
- evidence index commit: `4425edbe8e29912ff44d41da2a5e458bdac292d3`
- independent verification: `f1bb1cfcefbd7a3b5abb2a4f3bf6b4c00707605e`

Do not rerun this exact acceptance task without regression evidence.

### Commercial kernel hardening

Completed:

- Codex admin/bridge auth-context verification and preflight;
- canonical terminal states and terminal polling stop;
- transaction-safe queue kernel;
- atomic claim, leases, heartbeat and execution deadline;
- cancellation and rollback before delivery;
- bounded explicit retry with lineage;
- concurrency control;
- intake v2 and bridge v3;
- GitHub evidence and remote-SHA verification.

### OpenClaw/Harness technical work

Completed:

- existing OpenClaw runtime discovery without reinstall;
- OpenClaw provider probe;
- Agent Harness backend integration;
- public chat POST Nginx repair;
- status-code intent-boundary regression repair;
- negative secret-constraint classification repair.

These do not make the custom Web Console the approved product UI.

## Current task

Task ID:

`commercial-native-openclaw-ui-20260617`

Status:

`native_openclaw_ui_switch_pending`

Immediate action:

- read-only discover native OpenClaw UI, WebSocket, auth/pairing, session/history capabilities and effective Nginx routing;
- commit sanitized discovery evidence;
- then build a reversible root-route migration;
- do not submit another product task before browser acceptance.

## Controlled product task with open gap

Task:

`chat-oris-final-acceptance-api-20260617-051313-c802347ff17c`

Product commit:

`927f1968cc86bfd5213670f4eaa171fc1a3be620`

Implemented `/capabilities` and tests, but omitted the explicitly requested README API-list update. Treat as partially delivered until repaired and fully re-verified.

## Historical documents

These remain useful as evidence/history but are not current operational truth where they conflict with 2026-06-17 files:

- `memory/dev_employee/CURRENT_STATE_2026-06-16.md`
- `memory/dev_employee/NEXT_CHAT_HANDOFF_2026-06-16.md`
- `memory/dev_employee/NEW_CHAT_BOOTSTRAP_PROMPT_2026-06-16.md`
- the Codex-auth-invalid sections of 2026-06-16 environment/engineering docs;
- older sections of `docs/PROJECT_STATE.md`;
- older sections of `memory/HANDOFF.md`.

## Fixed interaction contract

- Chinese, professional, direct and structured;
- do not ask the user to choose routine engineering details;
- write long scripts/docs/patches directly to GitHub;
- give one short command to fetch/run the GitHub file;
- avoid long heredocs because terminal commands may be truncated;
- inspect logs from GitHub;
- every user-run script ends with `===== SUMMARY =====`;
- the user sends only the SUMMARY block;
- never print or commit secrets;
- no `set -e` in user-facing scripts;
- one mainstream branch: `main`;
- backups allowed, competing long-lived branches prohibited;
- ORIS owns platform/evidence; product repositories own product code/docs/tests;
- layered, decoupled and configuration-separated design;
- build generic commercial mechanisms;
- completion requires every requested deliverable, tests, product SHA, remote SHA and ORIS evidence.
