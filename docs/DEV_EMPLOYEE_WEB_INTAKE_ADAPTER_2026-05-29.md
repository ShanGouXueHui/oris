# Dev Employee Web Intake Adapter — 2026-05-29

## Purpose

This document defines the first local Web/OpenClaw adapter contract for ORIS Dev Employee.

The adapter is intentionally thin. It converts a UI/OpenClaw payload into calls to the already-verified local intake service. It does not execute shell commands, invoke Codex, write queue files directly, or push GitHub.

## Script

```text
scripts/dev_employee_web_intake_adapter.py
```

Commands:

```text
projects
submit --payload <json-file>
status --task-id <task-id>
```

## Request model

A Web/OpenClaw caller should submit a JSON object with these fields:

```json
{
  "project_key": "oris-final-acceptance-api",
  "task_id": "optional-stable-task-id",
  "objective": "A concrete product development goal with acceptance criteria.",
  "constraints": [
    "Do not ask the human for routine engineering decisions.",
    "Do not add external dependencies unless necessary."
  ],
  "expected_checks": [
    "/home/admin/projects/oris-final-acceptance-api/.venv/bin/python -m pytest -q"
  ],
  "commit_message": "feat(api): implement requested goal",
  "notes": ["Submitted through Web/OpenClaw adapter"]
}
```

Required:

- `project_key`
- `objective`

Optional:

- `task_id`
- `constraints`
- `expected_checks`
- `commit_message`
- `notes`

## Local commands

List available projects:

```bash
python3 scripts/dev_employee_web_intake_adapter.py projects
```

Submit a goal:

```bash
python3 scripts/dev_employee_web_intake_adapter.py submit --payload /path/to/payload.json
```

Query status:

```bash
python3 scripts/dev_employee_web_intake_adapter.py status --task-id <task-id>
```

## Security boundaries

- Adapter only talks to loopback intake URL.
- Adapter reads intake token from local environment or local config file.
- Adapter does not print token values.
- Adapter does not accept arbitrary filesystem write targets.
- Product path/repo resolution remains owned by the intake service and project registry.
- Public exposure is not part of this step. If later exposed via Nginx/OpenClaw Web, add explicit auth and reverse proxy policy first.

## Evidence flow

```text
Web/OpenClaw payload
  -> dev_employee_web_intake_adapter.py
  -> local intake service
  -> intake catalog
  -> enqueue API
  -> supervised bridge
  -> Codex CLI
  -> product commit/push
  -> ORIS evidence
  -> status query returns evidence paths
```

## Next validation

Run an adapter smoke without letting the bridge consume the task:

1. Stop bridge temporarily.
2. Submit a small smoke payload via adapter.
3. Query status via adapter.
4. Remove smoke queue/catalog/prompt.
5. Restart bridge.

After that, run one tiny real goal through the adapter to prove full Web/OpenClaw-to-Codex path.
