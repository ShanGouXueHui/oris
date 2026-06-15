# ORIS Dev Employee — Next Chat Handoff

Date: 2026-06-16

## Start here

Read in this exact order:

1. `memory/dev_employee/CONTEXT_INDEX.md`
2. `memory/dev_employee/CURRENT_STATE_2026-06-16.md`
3. `memory/dev_employee/current_task.json`
4. `memory/dev_employee/current_task.md`
5. `docs/DEV_EMPLOYEE_COMMERCIAL_ARCHITECTURE_2026-06-16.md`
6. `docs/DEV_EMPLOYEE_ENVIRONMENT_AND_OPERATING_MODEL_2026-06-16.md`
7. `docs/DEV_EMPLOYEE_ENGINEERING_STANDARD_2026-06-16.md`
8. `docs/DEV_EMPLOYEE_AUTONOMOUS_EXECUTION_POLICY.md`
9. `orchestration/project_registry.json`
10. latest evidence for task `goal-oris-final-acceptance-api-20260616-031022`

## Current commercial objective

Continue productizing ORIS as a generic, secure, autonomous AI development employee.

The immediate objective is not to redesign the architecture. It is to restore the coding executor, harden the task lifecycle, and complete one real public-Web-to-GitHub project task.

## Current system state

Working:

- public control entry at `https://control.orisfy.com`;
- HTTPS and Basic Auth;
- persistent public Web submission;
- inner Console Token authorization;
- project allowlist;
- loopback-only Web Console and intake services;
- supervised bridge;
- task queue/catalog/status;
- strict result schema;
- GitHub failure evidence and triage;
- public Web UI project selection and JavaScript execution.

Current allowlisted project:

- `oris-final-acceptance-api`

Current services:

- `oris-dev-employee-web-console.service`: active
- `oris-dev-employee-intake.service`: active
- `oris-dev-employee-bridge.service`: active

## Current failed real task

Task id:

`goal-oris-final-acceptance-api-20260616-031022`

Status:

`codex_failed`

Requested change:

- add `GET /readonly-e2e`;
- exact JSON `{"readonly_e2e": true}`;
- add pytest coverage;
- test, commit, and push.

What happened:

- public Web submission succeeded;
- intake returned HTTP 201;
- bridge claimed the task;
- Codex started;
- Codex authentication failed before product mutation;
- product commit/remote SHA are absent;
- failure evidence was committed.

Evidence:

- failure evidence commit: `ea2089c5344c67e016601de8993ef365591daa06`
- diagnostic commit: `6fbc0ba1636ca01865b9565e68fdf6689ed6cae5`
- Codex log: `logs/dev_employee/goal-oris-final-acceptance-api-20260616-031022.codex.log`
- diagnostic log: `logs/dev_employee/codex_failed_diagnostics/goal-oris-final-acceptance-api-20260616-031022-20260616031848.log`

Root cause classification:

`codex_authentication`

## First action in the next chat

Do not submit another real product task immediately.

First:

1. inspect the latest Codex failure evidence from GitHub;
2. add a GitHub-hosted reauthentication/preflight validation script;
3. have the user run one short command;
4. verify a harmless non-interactive Codex execution as `admin`;
5. verify the bridge service sees the same auth context;
6. add auth preflight to the bridge;
7. update terminal-state handling;
8. rerun the feature with a new task id.

## Required lifecycle fixes

The next implementation must include:

- treat `codex_failed` as terminal;
- stop Web E2E polling on all terminal failures;
- normalize detailed failure codes into a canonical state model;
- executor auth health check before claiming or executing a task;
- clear status/evidence output for authentication failures;
- no implicit infinite retry;
- explicit retry using a new attempt/task identity.

## User interaction rules

- communicate in Chinese;
- professional, direct, structured;
- do not ask the user to choose routine engineering details;
- modify GitHub directly for scripts and documents;
- user should run only short copy-paste commands or GitHub-hosted `.sh` scripts;
- inspect logs from GitHub instead of asking for long pasted output;
- every operational script must end with `===== SUMMARY =====`;
- user sends only the SUMMARY block;
- never include secrets in GitHub, logs, SUMMARY, or chat;
- do not use `set -e` in user-facing Linux scripts.

## Engineering rules

- layered and decoupled architecture;
- config/secrets/runtime separation;
- ORIS owns orchestration, product repos own product code;
- `main` is the only mainstream branch;
- backups are allowed, competing long-lived branches are not;
- build generic commercial components, not acceptance-project forks;
- exact tests, commits, and remote SHA are required for completion;
- public intake port 18892 must remain unexposed.

## Environment anchors

- ORIS execution host: `43.106.55.255`, user `admin`
- ORIS repo: `/home/admin/projects/oris`
- product repo: `/home/admin/projects/oris-final-acceptance-api`
- public entry: `https://control.orisfy.com`
- separate production host: `8.136.28.6`, user `deploy`; do not touch without an explicit production task

## Definition of the next successful milestone

The next milestone is complete only when a new public Web task:

1. is submitted through `control.orisfy.com`;
2. passes executor auth preflight;
3. changes only the product repository;
4. passes compile and pytest checks;
5. creates a product commit;
6. pushes and verifies product remote SHA;
7. creates ORIS evidence commit;
8. reaches `completed` in Web status;
9. leaves security controls enabled;
10. produces a concise SUMMARY and GitHub-backed evidence.
