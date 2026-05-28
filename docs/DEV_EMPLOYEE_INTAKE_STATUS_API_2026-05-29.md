# Dev Employee Intake and Status API — 2026-05-29

## Purpose

This document defines the first productized local intake/status contract for ORIS Dev Employee.

The API is intended for OpenClaw Web or other non-shell callers. A caller submits a target project, objective, constraints, and expected checks. ORIS writes a runtime prompt, submits the task to the existing loopback enqueue API, persists a small catalog record, and exposes status/evidence lookup by task id.

## Scope

The intake API is deliberately thin.

It does:

- resolve `project_key` through `orchestration/project_registry.json`;
- write runtime prompt under `run/dev_employee_prompts/`;
- submit the task to existing `dev_employee_enqueue_server.py`;
- annotate queued descriptor with strict autonomous metadata;
- persist catalog records under `orchestration/dev_employee_intake_catalog/`;
- expose status/evidence aggregation.

It does not:

- invoke Codex directly;
- execute shell commands;
- push GitHub commits;
- bypass the supervised bridge;
- accept non-loopback binding;
- expose secrets.

## Script

```text
scripts/dev_employee_intake_api.py
```

Default bind:

```text
127.0.0.1:18892
```

Environment:

```text
ORIS_DEV_EMPLOYEE_INTAKE_TOKEN=<local-only intake token>
ORIS_DEV_EMPLOYEE_ENQUEUE_TOKEN=<existing enqueue token>
ORIS_DEV_EMPLOYEE_INTAKE_PORT=18892
ORIS_DEV_EMPLOYEE_INTAKE_HOST=127.0.0.1
```

The API also reads `~/.config/oris/dev_employee_enqueue.env` for local tokens. Do not commit that file.

## Endpoints

### `GET /health`

Returns service health.

Response:

```json
{
  "status": "ok",
  "service": "dev_employee_intake_api"
}
```

### `GET /projects`

Returns available project keys from `orchestration/project_registry.json`.

Response:

```json
{
  "projects": ["oris", "oris-final-acceptance-api"]
}
```

### `POST /goals`

Submits a goal-driven Dev Employee task.

Headers:

```text
X-ORIS-Token: <ORIS_DEV_EMPLOYEE_INTAKE_TOKEN>
Content-Type: application/json
```

Request body:

```json
{
  "project_key": "oris-final-acceptance-api",
  "task_id": "goal-example-20260529-r1",
  "objective": "Add a small deterministic endpoint and tests. Keep all existing tests passing.",
  "constraints": [
    "Do not ask the human for routine engineering decisions.",
    "Do not add external dependencies."
  ],
  "expected_checks": [
    "/home/admin/projects/oris-final-acceptance-api/.venv/bin/python -m pytest -q",
    "/home/admin/projects/oris-final-acceptance-api/.venv/bin/python -m pytest -q -W error::DeprecationWarning"
  ],
  "commit_message": "feat(api): add example endpoint",
  "notes": ["Queued from OpenClaw/Web intake API"]
}
```

Behavior:

1. Resolve product path/repo from project registry.
2. Write runtime prompt.
3. POST to local enqueue API.
4. Annotate descriptor with:
   - `strict_result_schema=true`
   - `autonomy_mode=goal_driven`
   - `task_objective`
   - `constraints`
   - `expected_checks`
5. Write catalog record.

### `GET /goals`

Lists catalog records.

### `GET /goals/<task_id>`

Returns aggregated status:

- intake catalog record;
- queue descriptor if present;
- run/evidence JSON files;
- latest progress snapshot;
- direct evidence paths.

## Security boundaries

- Bind loopback only.
- Require token unless explicitly allowed by local environment for testing.
- Do not accept arbitrary product paths; use project registry only.
- Do not execute commands.
- Do not commit secrets.
- Do not expose or print local token values.

## Integration path

Recommended next implementation step:

1. Add a systemd user service for `dev_employee_intake_api.py`.
2. Add a smoke script that starts the service, submits a tiny no-op or test project goal, and verifies catalog/status behavior.
3. Add Nginx/OpenClaw Web routing only after local loopback and token behavior is verified.
4. Keep GitHub evidence as the source of truth for completed work.

## Evidence policy

A completed intake task should be considered valid only when the status response links to GitHub-verifiable evidence:

- product commit SHA;
- product remote SHA;
- ORIS evidence JSON;
- skill resolver report;
- host check logs;
- optional acceptance harness report.
