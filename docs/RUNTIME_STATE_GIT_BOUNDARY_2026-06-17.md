# ORIS Runtime State Git Boundary — 2026-06-17

## Decision

Live runtime state, telemetry, append-only execution logs, chat-session content, and Agent Harness traces are operational data. They are not source code, configuration authority, or durable Git evidence.

The following files were historically tracked but are generated and continuously updated by the running system:

- `orchestration/active_routing.json`
- `orchestration/runtime_plan.json`
- `orchestration/runtime_state.json`
- `orchestration/execution_log.jsonl`
- `logs/dev_employee/free_mesh_latency_events.jsonl`

They are now removed from the Git index and explicitly ignored. Existing server copies remain at the same paths so running services are not disrupted.

## Sensitive conversational runtime

The following runtime locations must never be committed because they may contain user content or detailed routing traces:

- `orchestration/dev_employee_chat_sessions/`
- `logs/dev_employee/agent_harness/*.jsonl`

Sanitized, task-specific acceptance evidence may still be written under versioned evidence directories, but raw conversations and raw Harness event streams remain local runtime data.

## Authority model

- Git: source code, declarative policy, schemas, tests, documentation, sanitized acceptance evidence.
- Runtime filesystem: current routing state, health counters, live plans, append-only operational logs, chat sessions, raw traces.
- ORIS task/evidence model: commercial task lifecycle and delivery evidence.

Git must not be used as a live state database.

## Deployment implications

Deployment scripts must not stash or restore generated runtime files. They must:

1. protect only non-runtime tracked edits;
2. leave generated state in place;
3. validate services and product repositories independently;
4. commit only sanitized evidence;
5. avoid uploading raw conversation or provider trace content.

## Migration safety

The one-time migration archives the failed pre-deployment stash under an admin-only local state directory with SHA256 checksums. Current live files remain authoritative and unchanged. The stash is dropped only after backup integrity and file preservation are verified.
