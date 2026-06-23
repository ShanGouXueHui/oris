# Next Chat Handoff: ORIS Autonomous Runtime v2

Date: 2026-06-23

## Read first

The next chat must not rely on prior chat context. Read these files from GitHub in order:

1. `memory/dev_employee/CURRENT_STATE_2026-06-22_AUTONOMOUS_RUNTIME_V2.md`
2. `memory/dev_employee/NEXT_CHAT_START_PROMPT_2026-06-22_RUNTIME_V2_MODULE_B.md`
3. `memory/dev_employee/ENGINEERING_GUARDRAILS_SCRIPT_AND_EVIDENCE_2026-06-22.md`
4. `docs/DEV_EMPLOYEE_AUTONOMOUS_RUNTIME_V2_ACCEPTANCE_2026-06-22.md`
5. `docs/OPERATING_CONTEXT_AND_ENGINEERING_RULES_2026-06-22_RUNTIME_V2.md`
6. `orchestration/project_registry.json`
7. `memory/dev_employee/current_task.json`
8. `memory/dev_employee/current_task.md`
9. GitHub issue `https://github.com/ShanGouXueHui/oris/issues/15`

Then inspect the current latest commits in:

- `ShanGouXueHui/oris`
- `ShanGouXueHui/oris-commercial-insight-employee`

## Current facts

- Runtime v2 acceptance issue exists: `https://github.com/ShanGouXueHui/oris/issues/15`.
- Runtime v2 authority doc exists: `docs/DEV_EMPLOYEE_AUTONOMOUS_RUNTIME_V2_ACCEPTANCE_2026-06-22.md`.
- Runtime v2 Module A is accepted.
- Module A final commit: `c244e2467fe153377b370df0ffc35d541b8b3ef1`.
- Module A evidence commit recorded inside report: `a785cef3fb7fd5b5f3403a568d1e701a9e72ac13`.
- Runtime v2 Module B is accepted.
- Module B final commit: `68a704da3f03bff31206f90cb5806f240c8ba9f6`.
- Module B evidence commit recorded inside report: `c5f732672d8d3080e4c56af4ff3fccb945a95bf5`.
- Module B latest test result: `reports/testing/latest_test_result.json` with `status=passed` and `test_exit_code=0`.
- Module B execution report: `reports/execution/module_B_execution_report.md`.
- Insight product Module 0 commit remains: `7d1d604b92b21f1213f990140b3345b4be2163ca`.
- Product repo was checked read-only by `git ls-remote`; old interactive insight product was not continued.

## Strategic direction

Do not continue expanding the interactive insight product as the main line.

The priority is:

```text
Upgrade ORIS -> Autonomous Dev Employee Runtime v2 -> use upgraded ORIS to rebuild/recreate insight capability as acceptance demo.
```

## Immediate next task

Start Runtime v2 Module C: Autonomous Worker Loop and Repair Policy.

Module C should connect the persistent substrate from Module B to a bounded autonomous worker iteration:

- worker loop contract;
- context pack loading rule;
- queue claim -> run transition -> task execution stub -> test evidence -> commit/evidence decision flow;
- retryable failure repair policy;
- blocked/fatal failure handling;
- approval gate handling for high-risk actions;
- tests for successful worker iteration, retryable repair path, blocked approval path, terminal protection, and event evidence;
- `docs/testing/MODULE_C_TEST_PLAN.md`;
- `reports/testing/module_C_test_result.json`;
- `reports/testing/latest_test_result.json`;
- `reports/execution/module_C_execution_report.md`.

Module C cannot be marked complete unless implementation and evidence are committed and pushed to GitHub.

## Script and evidence guardrail

The user explicitly corrected the process after Module A: do not create many compatibility scripts or parallel executable versions. This is a binding memory in:

- `memory/dev_employee/ENGINEERING_GUARDRAILS_SCRIPT_AND_EVIDENCE_2026-06-22.md`

The assistant must obey:

- one official executable entry point per workflow only;
- no `_v2.sh`, `_v3.sh`, `compat.sh`, or similar script proliferation unless explicitly approved;
- old executable script versions are backed up by Git history, not by extra repo files;
- before asking the user to rerun a script, verify GitHub state and remove duplicate executable entry points;
- keep terminal output short;
- read reports/logs from GitHub instead of asking the user to paste long logs;
- ORIS platform validation must not mutate product repositories unless explicitly required.

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
- Do not create duplicate executable bootstrap scripts for the same workflow.

## Desired end state

A verifier can inspect GitHub and confirm that ORIS autonomously decomposes, develops, tests, repairs, commits, pushes, records evidence, deploy-smoke-tests, and finally rebuilds insight capability without routine human decisions.
