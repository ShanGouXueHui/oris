# Dev Employee Local Enqueue API Runbook

## Purpose

Expose a loopback-only HTTP intake for ORIS Dev Employee tasks.

The API only creates local queued task descriptor files under:

`/home/admin/projects/oris/orchestration/dev_employee_queue/`

It does not execute shell commands, does not invoke Codex, and does not push GitHub. The existing supervised bridge service watches the queue and performs execution.

## Server script

`/home/admin/projects/oris/scripts/dev_employee_enqueue_server.py`

Default bind:

`127.0.0.1:18891`

## Start manually for smoke test

```bash
cd /home/admin/projects/oris

export ORIS_DEV_EMPLOYEE_ENQUEUE_TOKEN='replace-with-local-random-token'
python3 scripts/dev_employee_enqueue_server.py
```

## Health check

```bash
curl -s http://127.0.0.1:18891/health
```

## Enqueue request

```bash
curl -s -X POST http://127.0.0.1:18891/enqueue \
  -H "Content-Type: application/json" \
  -H "X-ORIS-Token: $ORIS_DEV_EMPLOYEE_ENQUEUE_TOKEN" \
  -d '{
    "task_id": "bridge-service-smoke-http-20260525",
    "prompt_path": "/home/admin/projects/oris/prompts/dev_employee_bridge_service_smoke_20260525.md",
    "product_path": "/home/admin/projects/oris-final-acceptance-api",
    "product_repo": "ShanGouXueHui/oris-final-acceptance-api",
    "commit_message": "test(dev-employee): bridge service http enqueue smoke",
    "note": "Queued through local enqueue HTTP API"
  }'
```

## Queue check

```bash
curl -s http://127.0.0.1:18891/queue
```

## Security notes

- Bind only to loopback.
- Require `X-ORIS-Token` for POST `/enqueue`.
- Do not expose this server directly through Nginx.
- If OpenClaw Web calls this API, proxy only from local trusted process context.
- Queue JSON files are local runtime state and ignored by Git.
