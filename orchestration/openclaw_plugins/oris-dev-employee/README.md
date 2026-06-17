# ORIS Dev Employee OpenClaw Plugin

Status: source-only validation candidate. Do not install or enable before the isolated validation gate passes.

## v0.1 capabilities

Optional read-only tools:

- `oris_queue_status`
- `oris_task_status`
- `oris_latest_task_status`

Observation-only hooks:

- `model_call_ended`
- `after_tool_call`
- `agent_end`

The plugin calls only the loopback ORIS status/enqueue service at `127.0.0.1:18891`. v0.1 does not submit, cancel, retry or mutate product tasks.

Telemetry is local JSONL runtime state. It never records prompt text, model output, tool parameters, tool result content, raw session ids, credentials or headers.

## Build

The repository-managed validation script copies this package into a temporary directory, installs build dependencies there, links the existing OpenClaw installation for SDK resolution, compiles, tests and runs `openclaw plugins validate`.

Do not run `openclaw plugins install` manually.
