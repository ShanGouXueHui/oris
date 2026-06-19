---
name: oris-readonly-status
description: Mandatory live routing for ORIS queue and task status requests. Always use the approved ORIS typed read-only tool and never answer from memory, exec, or write actions.
user-invocable: false
metadata: {"openclaw":{"os":"linux"}}
---

# ORIS read-only status routing

Use this skill for every request about the current ORIS Dev Employee queue, a specific ORIS task, the latest ORIS task, execution progress, or the next step of an existing task.

## Mandatory live lookup

A live status request must call exactly the corresponding approved typed tool before producing the answer. Never answer from memory, previous turns, cached status, repository files, or inference.

- Current queue, running tasks, or whether anything is active: call `oris_queue_status`.
- A named task ID or one specific task: call `oris_task_status` with that task ID.
- The latest, most recent, or current task snapshot: call `oris_latest_task_status`.

Canonical typed tool identifiers:

- `oris_queue_status`
- `oris_task_status`
- `oris_latest_task_status`

When several status questions are asked in one message, call each required typed tool. Do not substitute one tool's result for another tool's scope.

## Safety boundary

- These requests are read-only.
- Never use `exec`, shell commands, filesystem tools, browser tools, web requests, or direct HTTP as a fallback for ORIS status.
- Never submit, enqueue, cancel, retry, update, or otherwise mutate an ORIS task.
- Never infer live status from memory or prior conversation.
- If the required typed tool is unavailable or fails, state that the live status could not be retrieved. Do not switch to another tool class.

## Response behavior

Summarize only the sanitized typed-tool result in natural language. Do not require slash commands, special ORIS command syntax, or internal implementation details from the user.
