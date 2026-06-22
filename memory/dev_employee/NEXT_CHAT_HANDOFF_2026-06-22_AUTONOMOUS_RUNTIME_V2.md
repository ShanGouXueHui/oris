# Next Chat Handoff: ORIS Autonomous Runtime v2

Date: 2026-06-22

## Read first

The next chat must not rely on prior chat context. Read these files from GitHub in order:

1. `memory/dev_employee/CURRENT_STATE_2026-06-22_AUTONOMOUS_RUNTIME_V2.md`
2. `memory/dev_employee/NEXT_CHAT_START_PROMPT_2026-06-22_AUTONOMOUS_RUNTIME_V2.md`
3. `docs/DEV_EMPLOYEE_AUTONOMOUS_RUNTIME_V2_ACCEPTANCE_2026-06-22.md`
4. `docs/OPERATING_CONTEXT_AND_ENGINEERING_RULES_2026-06-22_RUNTIME_V2.md`
5. `orchestration/project_registry.json`
6. `memory/dev_employee/current_task.json`
7. `memory/dev_employee/current_task.md`
8. GitHub issue `https://github.com/ShanGouXueHui/oris/issues/15`

Then inspect the current latest commits in:

- `ShanGouXueHui/oris`
- `ShanGouXueHui/oris-commercial-insight-employee`

## Current facts

- Runtime v2 acceptance issue exists: `https://github.com/ShanGouXueHui/oris/issues/15`.
- Runtime v2 authority doc exists: `docs/DEV_EMPLOYEE_AUTONOMOUS_RUNTIME_V2_ACCEPTANCE_2026-06-22.md`.
- Authority doc commit: `01f828ba1c20995dd1c69a4540a55c92ea93087f`.
- Current state archive commit: `ce9b5f57b2183416785a7b48f4c0da3b049e993f`.
- Insight product Module 0 commit: `7d1d604b92b21f1213f990140b3345b4be2163ca`.
- Module 1 modularization was prompted, but not verified complete in this chat.
- SSH command to `admin@43.106.55.255` failed with `Permission denied (publickey)`.

## Strategic direction

Do not continue expanding the interactive insight product as the main line.

The priority is:

```text
Upgrade ORIS -> Autonomous Dev Employee Runtime v2 -> use upgraded ORIS to rebuild/recreate insight capability as acceptance demo.
```

## Immediate next task

Start Runtime v2 Module A: Architecture and State Machine Design.

Module A deliverables:

- architecture doc;
- state machine schema;
- failure taxonomy;
- acceptance criteria;
- tests for status transitions;
- `docs/testing/MODULE_A_TEST_PLAN.md`;
- `reports/testing/module_A_test_result.json`;
- `reports/testing/latest_test_result.json`;
- `reports/execution/module_A_execution_report.md`.

Module A cannot be marked complete unless implementation and evidence are committed and pushed to GitHub.

## Operational blocker

The user tried to run the SSH bootstrap command and got:

```text
admin@43.106.55.255: Permission denied (publickey)
```

This is an access/auth problem, not an ORIS code problem.

Use one of these routes:

1. user runs commands inside an already authenticated terminal on `43.106.55.255`;
2. user fixes local SSH key access to `admin@43.106.55.255`;
3. use ORIS/OpenClaw Web if it has sufficient write/execute actions;
4. use GitHub connector for repo docs/issues, but note it cannot kill remote processes or run server commands.

## Verification protocol

Only accept progress when GitHub has:

- commit SHA;
- test plan;
- test result JSON;
- execution report;
- evidence index or ORIS run evidence.

Do not accept OpenClaw UI text alone.

## Do not do

- Do not rely on long OpenClaw chat history.
- Do not build product business logic inside ORIS except acceptance/demo orchestration references.
- Do not enable unbounded generic exec/write tools.
- Do not execute unvalidated downloaded skills.
- Do not touch Hangzhou production host `8.136.28.6` unless explicitly authorized.
- Do not commit credentials, tokens, private env files, or secrets.
- Do not use `set -e` in copy-paste commands.

## Desired end state

A verifier can inspect GitHub and confirm that ORIS autonomously decomposes, develops, tests, repairs, commits, pushes, records evidence, deploy-smoke-tests, and finally rebuilds insight capability without routine human decisions.
