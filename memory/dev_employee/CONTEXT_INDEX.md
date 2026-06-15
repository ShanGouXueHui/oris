# ORIS Dev Employee — Authoritative Context Index

Last updated: 2026-06-16

## Purpose

This file is the stable entry point for every new ORIS Dev Employee conversation.
Do not reconstruct the project from chat history when these GitHub files are available.

## Mandatory read order

1. `memory/dev_employee/FINAL_ACCEPTANCE_COMPLETION_2026-06-16.md`
2. `memory/dev_employee/current_task.json`
3. `memory/dev_employee/current_task.md`
4. `docs/DEV_EMPLOYEE_QUEUE_LIFECYCLE_HARDENING_2026-06-16.md`
5. `memory/dev_employee/CURRENT_STATE_2026-06-16.md`
6. `memory/dev_employee/NEXT_CHAT_HANDOFF_2026-06-16.md`
7. `docs/DEV_EMPLOYEE_COMMERCIAL_ARCHITECTURE_2026-06-16.md`
8. `docs/DEV_EMPLOYEE_ENVIRONMENT_AND_OPERATING_MODEL_2026-06-16.md`
9. `docs/DEV_EMPLOYEE_ENGINEERING_STANDARD_2026-06-16.md`
10. `docs/DEV_EMPLOYEE_AUTONOMOUS_EXECUTION_POLICY_ADDENDUM_2026-06-16.md`
11. `docs/DEV_EMPLOYEE_AUTONOMOUS_EXECUTION_POLICY.md`
12. `orchestration/project_registry.json`
13. `memory/dev_employee/NEW_CHAT_BOOTSTRAP_PROMPT_2026-06-16.md`

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

## Completed prerequisite

The first real public Web commercial-chain acceptance task is complete.

- task id: `goal-oris-final-acceptance-api-readonly-e2e-20260616-044030`
- status: `completed`
- product commit and remote SHA: `3207f20a2afdf109beac9a4a95523e7792e0ae33`
- ORIS evidence commit and remote SHA: `188a17eeba4acb43f5b922560ad98c3d8d28c587`
- ORIS evidence index commit: `4425edbe8e29912ff44d41da2a5e458bdac292d3`
- independent final verification log commit: `f1bb1cfcefbd7a3b5abb2a4f3bf6b4c00707605e`

Do not rerun this acceptance project unless regression evidence shows that the commercial chain has broken.

## Current task

Commercial hardening P1-A is prepared and pending server-side deployment:

- task id: `commercial-hardening-queue-lifecycle-20260616`
- scope: transaction-safe filesystem queue, canonical lifecycle, lease/heartbeat, timeout, cancel/rollback, explicit retry, concurrency slots, event ledger, and safe stale expiry;
- deployment acceptance submits no real product task;
- browser testing is deferred until server-side deployment passes;
- the operator will perform browser testing from `https://control.orisfy.com` when requested.

After P1-A passes, continue with RBAC/audit/security, monitoring/SLO/backup, and generic project onboarding.
