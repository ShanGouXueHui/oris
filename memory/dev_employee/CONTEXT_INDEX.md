# ORIS Dev Employee — Authoritative Context Index

Last updated: 2026-06-16

## Purpose

This file is the stable entry point for every new ORIS Dev Employee conversation.
Do not reconstruct the project from chat history when these GitHub files are available.

## Mandatory read order

1. `memory/dev_employee/CURRENT_STATE_2026-06-16.md`
2. `memory/dev_employee/NEXT_CHAT_HANDOFF_2026-06-16.md`
3. `memory/dev_employee/current_task.json`
4. `memory/dev_employee/current_task.md`
5. `docs/DEV_EMPLOYEE_COMMERCIAL_ARCHITECTURE_2026-06-16.md`
6. `docs/DEV_EMPLOYEE_ENVIRONMENT_AND_OPERATING_MODEL_2026-06-16.md`
7. `docs/DEV_EMPLOYEE_ENGINEERING_STANDARD_2026-06-16.md`
8. `docs/DEV_EMPLOYEE_AUTONOMOUS_EXECUTION_POLICY_ADDENDUM_2026-06-16.md`
9. `docs/DEV_EMPLOYEE_AUTONOMOUS_EXECUTION_POLICY.md`
10. `orchestration/project_registry.json`
11. `memory/dev_employee/NEW_CHAT_BOOTSTRAP_PROMPT_2026-06-16.md`

## Authority hierarchy

When documents conflict, use this order:

1. latest dated file under `memory/dev_employee/`;
2. `memory/dev_employee/current_task.json`;
3. latest task/evidence files under `orchestration/task_runs/` and `logs/dev_employee/`;
4. current machine-readable configuration;
5. older dated state or handoff documents.

## Historical documents

The following remain useful as history but are not current operational truth:

- `memory/dev_employee/CURRENT_STATE_2026-05-23.md`
- `memory/dev_employee/NEXT_CHAT_HANDOFF_2026-05-23.md`
- older sections of `docs/PROJECT_STATE.md`
- older sections of `memory/HANDOFF.md`

Do not delete historical evidence. Correct current truth by adding a newer authoritative document rather than rewriting history.

## Current critical blocker

The public Web Console path is operational, but the first real public Web task failed at Codex execution because the executor login state is invalid.

Authoritative task:

- task id: `goal-oris-final-acceptance-api-20260616-031022`
- status: `codex_failed`
- root cause: `codex_authentication`
- diagnostic commit: `6fbc0ba1636ca01865b9565e68fdf6689ed6cae5`

The next conversation must repair and verify Codex authentication in the same host/service execution context before submitting a replacement task id.
