# OpenClaw Web to ORIS Dev Employee Enqueue Integration — 2026-05-26

## Current proven chain

The following chain has been verified with GitHub evidence:

```text
HTTP enqueue API
  -> local queue descriptor
  -> systemd supervised bridge
  -> Codex CLI
  -> runtime task contract injection
  -> local checks
  -> host-side final checks
  -> product GitHub verification
  -> ORIS evidence commit
```

Verified evidence commits:

- `bridge-service-smoke-http-20260525`: `7c861d3f2db084a8ac9724e954d51d2d79a8667d`
- `bridge-runtime-contract-smoke-20260526`: `776b7bb90666e562dc5b3e15fa6a902ff1790d38`

## Integration goal

OpenClaw Web must stop pretending to execute shell commands. It should become a task intake surface that calls the local enqueue API:

```text
POST http://127.0.0.1:18891/enqueue
```

The enqueue API creates a local queued task descriptor. The supervised bridge service performs all execution and evidence handling.

## Contract

### Request

```json
{
  "task_id": "unique-task-id",
  "prompt_path": "/home/admin/projects/oris/prompts/example.md",
  "product_path": "/home/admin/projects/oris-final-acceptance-api",
  "product_repo": "ShanGouXueHui/oris-final-acceptance-api",
  "commit_message": "test(dev-employee): example task",
  "note": "Queued from OpenClaw Web"
}
```

### Headers

```text
Content-Type: application/json
X-ORIS-Token: <local token from ~/.config/oris/dev_employee_enqueue.env>
```

### Response

```json
{
  "queued": true,
  "task_id": "unique-task-id",
  "path": "/home/admin/projects/oris/orchestration/dev_employee_queue/unique-task-id.queued.json"
}
```

## Security model

- The API binds only to `127.0.0.1`.
- The token is stored only in `~/.config/oris/dev_employee_enqueue.env`.
- The API does not execute commands.
- The API does not invoke Codex.
- The API does not commit or push GitHub.
- The bridge validates paths and performs execution under the host-side policy.
- Do not expose the enqueue API directly through public Nginx.

## OpenClaw Web behavior

OpenClaw Web should:

1. generate a task id;
2. select a prompt path already present under the ORIS repo;
3. call the enqueue API;
4. show the queued task id to the user;
5. poll or display `orchestration/task_runs/<task_id>.json` after completion;
6. never output pseudo `exec` or pseudo `write` as completion evidence.

## Completion evidence

A task is complete only when `orchestration/task_runs/<task_id>.json` has:

```json
{
  "status": "completed",
  "product_commit_sha": "...",
  "product_remote_sha": "...",
  "checks": {"ok": true}
}
```

and ORIS evidence has been committed to GitHub.

## Next implementation

Add a local enqueue client wrapper that OpenClaw Web or a local adapter can call without embedding curl snippets:

```text
scripts/dev_employee_enqueue_client.py
```

The client should read the token from `~/.config/oris/dev_employee_enqueue.env`, submit the JSON payload, and print only concise JSON output.
