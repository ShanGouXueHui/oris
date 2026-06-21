# Operating Context and Engineering Rules — 2026-06-22

## Working language and interaction style

- Default language: Chinese.
- Style: professional, direct, structured.
- Avoid long terminal paste requests when GitHub evidence exists.
- Prefer reading GitHub files, commits, run artifacts, and evidence records directly.
- When shell commands are needed, provide copy-paste ready commands.
- Do not use `set -e` in Linux commands for this user's environment.
- Keep commands small and staged.
- Avoid large screen output; write logs to `logs/`, `run/`, or `/tmp`, then tail key lines.

## Current environments

### Development machine

- Host: `43.106.55.255`
- User: `admin`
- ORIS local path: `/home/admin/projects/oris`
- Codex CLI is installed and authenticated.
- This is the main Dev Employee development and validation environment.

### Production machine

- Host: `8.136.28.6`
- User: `deploy`
- Use only when explicitly doing production-side work.

## Core repositories

### ORIS platform

- GitHub: `ShanGouXueHui/oris`
- Local path: `/home/admin/projects/oris`
- Role: platform orchestration, Dev Employee, routing, registry, governance, evidence, memory.
- Business application code should not be newly built inside ORIS.

### Final acceptance product

- GitHub: `ShanGouXueHui/oris-final-acceptance-api`
- Local path: `/home/admin/projects/oris-final-acceptance-api`
- Role: accepted test project for validating Codex-backed Dev Employee execution.

### Proposed insight product

- Proposed GitHub: `ShanGouXueHui/oris-commercial-insight-employee`
- Proposed local path: `/home/admin/projects/oris-commercial-insight-employee`
- Proposed project key: `oris-commercial-insight-employee`

## GitHub-first working rule

- Durable context must be written to GitHub.
- New chat continuation must read GitHub docs before making design or code changes.
- Evidence should include commit SHA, exact task id, exact test result, and artifact paths.
- If user output is incomplete, inspect GitHub artifacts before requesting more logs.

## Dev Employee validated loop

Validated with task `demo-openclaw-web-task-board-20260622015615`:

```text
OpenClaw / ORIS task intake
  -> ORIS queue/status API
  -> supervised bridge
  -> Codex CLI execution
  -> product repository checks
  -> product commit SHA capture
  -> ORIS evidence generation
  -> ORIS evidence commit and push
  -> status API terminal=true
  -> verifier acceptance=true
```

## Coding and architecture rules

- Layered design.
- Keep platform and product code separate.
- Separate configuration from business logic.
- Only one mainline branch should be treated as the active delivery branch.
- Backups or migration references are allowed, but avoid parallel active implementations.
- Generalize product design for commercial reuse; avoid one-off scripts becoming the product architecture.
- Preserve compatibility facades when refactoring modules used by existing entrypoints.
- Add regression tests when a compatibility issue is found.
- Do not hardcode environment-specific private values.
- Avoid broad writes into ignored runtime directories; force-add only bounded evidence files when required.

## Status and evidence rules

- `success` and `done` must classify as terminal `completed`.
- Status API should prioritize terminal run evidence over stale queue or catalog views.
- Product commit SHA is required for completed development work, including no-op completion where the product repository already contains the requested implementation.
- ORIS evidence must be committed and pushed for accepted tasks.

## Shell command rules

Use this style:

```bash
cd /home/admin/projects/oris
git status --short
git fetch origin
git pull --rebase --autostash origin main
```

Do not use this style:

```bash
set -e
```

## Log handling rule

When diagnosing:

1. read GitHub task run JSON first;
2. read Codex result JSON;
3. read evidence index;
4. read logs only if the above does not identify the issue;
5. ask the user for shell output only when the data is not committed or queryable.
