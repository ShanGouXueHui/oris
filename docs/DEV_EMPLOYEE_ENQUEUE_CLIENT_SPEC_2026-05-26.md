# Dev Employee Enqueue Client Spec — 2026-05-26

## Purpose

Provide a tiny local client wrapper for OpenClaw Web or a trusted local adapter to submit task descriptors to the loopback enqueue API.

This client should not execute shell commands, invoke Codex, or perform Git operations. It only sends one HTTP request to the local enqueue service.

## Inputs

Required CLI arguments:

- `--task-id`
- `--prompt-path`
- `--product-path`
- `--product-repo`
- `--commit-message`
- `--note` optional

Local configuration:

- Env file: `~/.config/oris/dev_employee_enqueue.env`
- Required key: `ORIS_DEV_EMPLOYEE_ENQUEUE_TOKEN`
- Endpoint: `http://127.0.0.1:18891/enqueue`

## Behavior

1. Read the local env file.
2. Extract `ORIS_DEV_EMPLOYEE_ENQUEUE_TOKEN`.
3. Submit JSON to the local enqueue API.
4. Print concise JSON containing HTTP status and API response.
5. Exit non-zero if the HTTP status is not 2xx.

## Security

- The token stays local and must never be committed.
- The endpoint must remain loopback-only.
- The client must not accept arbitrary non-loopback URLs unless an explicit local deployment policy later allows it.
- The client is a convenience wrapper, not an execution engine.

## Example usage

```bash
cd /home/admin/projects/oris

python3 scripts/dev_employee_enqueue_client.py \
  --task-id bridge-client-smoke-20260526 \
  --prompt-path /home/admin/projects/oris/prompts/dev_employee_bridge_service_smoke_20260525.md \
  --product-path /home/admin/projects/oris-final-acceptance-api \
  --product-repo ShanGouXueHui/oris-final-acceptance-api \
  --commit-message "test(dev-employee): client enqueue smoke" \
  --note "Queued through local enqueue client"
```
