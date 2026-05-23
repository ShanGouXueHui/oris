# Next Chat Handoff — ORIS Dev Employee

## Start here

Read these files first:

1. `memory/dev_employee/CURRENT_STATE_2026-05-23.md`
2. `docs/DEV_EMPLOYEE_AUTONOMOUS_EXECUTION_POLICY.md`
3. `orchestration/project_registry.json`
4. `prompts/dev_employee_new_project_task.md`
5. `prompts/dev_employee_existing_project_task.md`

## Current objective

Continue ORIS dev employee commercialization and final acceptance.

The immediate next task is to complete the final acceptance project:

- repo: `ShanGouXueHui/oris-final-acceptance-api`
- local path: `/home/admin/projects/oris-final-acceptance-api`
- type: independent test project
- stack: FastAPI + pytest + httpx
- function: small in-memory task-board API

## Important context

Do not rely on OpenClaw Web pseudo `exec/write` output. Real coding execution must use Codex CLI.

Codex CLI is installed and authenticated:

- binary: `/home/admin/.npm-global/bin/codex`
- version: `codex-cli 0.133.0`
- auth: ChatGPT login verified
- real filesystem execution: verified by `CODEX_REALITY_CHECK_OK`

GitHub CLI is authenticated:

- login: `ShanGouXueHui`
- protocol: SSH

The smoke project already passed remote creation/push:

- repo: `https://github.com/ShanGouXueHui/oris-dev-smoke-app`
- commit: `3754a51c921e2504bd246e209fe1868f13d55761`
- ORIS registry commit: `b73b8447b0c86e77b6ec294caf3080cb488189a4`

## Execution principles

- Use Chinese, professional, direct, structured responses.
- Do not print long scripts or long documents in chat. Upload/update GitHub files directly when possible.
- Prefer GitHub logs and commits as the memory substrate.
- Avoid `set -e` in Linux commands.
- Use one mainstream branch: `main`.
- Backups are allowed, but do not create competing long-lived branches unless explicitly requested.
- Keep platform code in ORIS and business/product code in independent repositories.
- Do not commit environment files, credential material, virtualenvs, caches, or runtime dirty files.
- Do not commit ORIS runtime noise unless explicitly requested:
  - `logs/dev_employee/free_mesh_latency_events.jsonl`
  - `orchestration/active_routing.json`
  - `orchestration/execution_log.jsonl`
  - `orchestration/runtime_plan.json`
  - `orchestration/runtime_state.json`

## Final acceptance requirements

For `oris-final-acceptance-api`, the final result must include:

- product repo URL;
- product local path;
- product commit SHA;
- ORIS registry commit SHA;
- changed files in product repo;
- changed files in ORIS repo;
- exact `python3 -m py_compile app/main.py` output;
- exact `pytest -q` output;
- confirmation that no product code was written inside `/home/admin/projects/oris`.

## Suggested next first action

Verify whether `oris-final-acceptance-api` already exists locally or remotely. Then run Codex CLI from the appropriate working directory.
