---
name: oris-readonly-status
description: Use ORIS typed read-only tools for queue and task status questions; never fall back to exec or write actions.
user-invocable: false
metadata: {"openclaw":{"os":"linux"}}
---

# ORIS read-only status routing

Use this skill whenever the user asks about the current ORIS Dev Employee queue, a specific ORIS task, the latest ORIS task, execution progress, or the next step of an existing task.

## Required tool routing

- Current queue, running tasks, or whether anything is active: call `oris_queue_status`.
- A named task ID or one specific task: call `oris_task_status` with that task ID.
- The latest, most recent, or current task snapshot: call `oris_latest_task_status`.

Canonical typed tool identifiers:

- `oris_queue_status`
- `oris_task_status`
- `oris_latest_task_status`

## Safety boundary

- These requests are read-only.
- Never use `exec`, shell commands, filesystem tools, browser tools, web requests, or direct HTTP as a fallback for ORIS status.
- Never submit, enqueue, cancel, retry, update, or otherwise mutate an ORIS task.
- Never infer live status from memory or prior conversation.
- If the required typed tool is unavailable or fails, state that the live status could not be retrieved. Do not switch to another tool class.

## Response behavior

Summarize only the sanitized typed-tool result in natural language. Do not require slash commands, special ORIS command syntax, or internal implementation details from the user.
