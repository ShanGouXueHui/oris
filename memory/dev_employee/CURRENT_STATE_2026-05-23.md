# ORIS Dev Employee State — 2026-05-23

## Summary

This archive captures the ORIS/OpenClaw/Codex state after the 2026-05-23 debugging and acceptance session.

Main conclusion: ORIS model routing and Codex host execution are usable. OpenClaw Web should be treated as the task intake and control layer. Real coding work should be executed through Codex CLI, with durable task state persisted to GitHub-backed files.

## Validated components

- OpenClaw Gateway is running behind `control.orisfy.com`.
- ORIS Free Mesh is exposed through a local OpenAI-compatible endpoint.
- OpenClaw default model was switched from `openrouter/auto` to native `oris/free-auto`.
- `oris/free-auto` is registered as provider `oris`, model id `free-auto`, local base URL `http://127.0.0.1:8789/v1`.
- Gateway token mode can remain as the control access layer.
- Codex CLI 0.133.0 is installed and logged in through ChatGPT.
- Codex CLI created a real host file `logs/dev_employee/codex_reality_check.txt` with `CODEX_REALITY_CHECK_OK`.
- GitHub CLI is logged in as `ShanGouXueHui` and configured for SSH Git operations.
- OpenClaw node host was installed and started.
- `coding-agent` and `github` skills are ready.

## Validated repositories and commits

### ORIS platform repo

- Repository: `https://github.com/ShanGouXueHui/oris`
- Local path: `/home/admin/projects/oris`
- Main branch is the only mainstream branch.

Important recent commits:

- `11780e2` — autonomous execution policy added.
- `b73b844` — `oris-dev-smoke-app` added to `orchestration/project_registry.json`.
- `169143d` — Codex real file execution smoke log.
- `81f40fc` — Codex login verified.
- `b4f6b62` — Codex CLI install log.
- `c62a4da` — minimal OpenClaw dev toolchain apply log.

### Smoke project repo

- Repository: `https://github.com/ShanGouXueHui/oris-dev-smoke-app`
- Local path: `/home/admin/projects/oris-dev-smoke-app`
- Product commit: `3754a51c921e2504bd246e209fe1868f13d55761`
- Purpose: verify that Codex-backed AI dev employee can create, test, commit, and push an independent GitHub repository.

## Current open issue

OpenClaw Web can still behave like a planner and output pseudo action text instead of autonomously continuing execution. This is not acceptable for commercial use.

The next design requirement is to connect OpenClaw Web task intake to Codex CLI execution with durable state, instead of relying on transient chat memory or pseudo tools.

## Current pending task

Final acceptance project is still pending:

- Repository: `ShanGouXueHui/oris-final-acceptance-api`
- Local path: `/home/admin/projects/oris-final-acceptance-api`
- Goal: create a standalone FastAPI task-board API with tests, push to GitHub, and register in ORIS registry.

Do not start this task until the next conversation has read this state archive and `docs/DEV_EMPLOYEE_AUTONOMOUS_EXECUTION_POLICY.md`.

## Working habits

- User prefers Chinese, professional, direct, structured responses.
- User prefers GitHub-backed durable memory over chat memory.
- Do not print long scripts or long documents in chat. Write them to GitHub and provide commit/file refs.
- Logs should be written under `logs/dev_employee/` and inspected from GitHub when possible.
- Linux commands should avoid `set -e`.
- Avoid committing environment files, credential material, virtualenvs, caches, and runtime noise.
- Keep separation of concerns: ORIS holds platform orchestration; product code lives in independent repositories.
