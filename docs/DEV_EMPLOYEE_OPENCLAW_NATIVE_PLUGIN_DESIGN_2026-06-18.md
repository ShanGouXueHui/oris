# ORIS Dev Employee — Native OpenClaw Plugin Design

Date: 2026-06-18
Status: design approved for isolated build validation; not installed or enabled

## 1. Decision

Build one external native OpenClaw plugin package owned by the ORIS platform repository:

`orchestration/openclaw_plugins/oris-dev-employee/`

The package is a mixed plugin built with `definePluginEntry` because it combines:

- typed agent tools;
- lifecycle and latency observation hooks;
- local loopback HTTP calls to ORIS;
- no channel, provider, model or custom Agent Harness implementation.

Do not modify OpenClaw core and do not reinstall or upgrade OpenClaw.

## 2. v0.1 tool contract

All v0.1 tools are read-only and optional.

### `oris_queue_status`

Purpose: inspect the local Dev Employee queue.

Backend:

`GET http://127.0.0.1:18891/queue`

Parameters: none.

Returned data is sanitized and bounded. The absolute queue directory is not returned to the model.

### `oris_task_status`

Purpose: inspect one known task id.

Backend:

`GET http://127.0.0.1:18891/task/{task_id}`

Parameters:

- `task_id`: 3–120 characters, letters, digits, dot, underscore or dash.

Returned data is recursively sanitized. Secret-like fields, prompt content, absolute host paths, environment data and raw credentials are removed.

### `oris_latest_task_status`

Purpose: inspect the latest Dev Employee progress snapshot.

Backend:

`GET http://127.0.0.1:18891/latest`

Parameters: none.

Returned data uses the same sanitizer and output-size limits.

## 3. Why submission is excluded from v0.1

The current `/enqueue` endpoint requires caller-supplied values including:

- `prompt_path`;
- `product_path`;
- `product_repo`;
- `commit_message`.

That endpoint is valid as a local engineering API, but it is not yet an appropriate direct model-facing action contract. A model-facing tool must not choose arbitrary host paths or bypass the project registry.

Therefore v0.1 does not register `oris_submit_task`, `oris_cancel_task` or `oris_retry_task`.

## 4. Required ORIS Action API v1 before write tools

Add a separate loopback-only action endpoint owned by ORIS, not by the plugin:

`POST /v1/actions/dev-employee-tasks`

Proposed request:

```json
{
  "project_id": "oris-final-acceptance-api",
  "goal": "Add a documented health endpoint",
  "acceptance_criteria": [
    "tests pass",
    "only the intended product repository changes",
    "commit and remote SHA are verified"
  ],
  "idempotency_key": "session-scoped-stable-key",
  "requested_by": {
    "surface": "openclaw",
    "session_hash": "non-secret-hash"
  }
}
```

The ORIS server, not the model or plugin, must resolve:

- product path and GitHub repository from `orchestration/project_registry.json`;
- prompt file location;
- task id;
- allowed scope and forbidden scope;
- commit message policy;
- queue descriptor;
- idempotency and duplicate handling;
- authorization and evidence policy.

Proposed response:

```json
{
  "accepted": true,
  "task_id": "...",
  "status": "queued",
  "status_resource": "/v1/actions/dev-employee-tasks/..."
}
```

Only after this contract exists and is tested may a side-effecting OpenClaw tool be added. It must be optional and protected by a `before_tool_call` approval hook with fail-closed timeout behavior.

## 5. Plugin configuration

The plugin accepts only non-secret configuration in v0.1:

- `baseUrl`, default `http://127.0.0.1:18891`;
- `requestTimeoutMs`, default `5000`;
- `telemetryEnabled`, default `true`;
- `telemetryPath`, default `~/.local/state/oris/openclaw-plugin/latency.jsonl`;
- `telemetryMaxBytes`, default `5242880`.

`baseUrl` must resolve to loopback HTTP. Non-loopback hosts, userinfo, query strings and fragments are rejected.

## 6. Tool policy

Manifest ownership:

```json
{
  "contracts": {
    "tools": [
      "oris_queue_status",
      "oris_task_status",
      "oris_latest_task_status"
    ]
  }
}
```

All three tools are marked optional in both runtime registration and `toolMetadata`.

The plugin can be installed without exposing tools to the model. Tool exposure requires an explicit `tools.allow` change after runtime inspection and smoke validation.

## 7. Telemetry contract

Register observation-only hooks:

- `model_call_ended`;
- `after_tool_call`;
- `agent_end`.

Each JSONL record may include:

- event type;
- UTC timestamp;
- duration in milliseconds;
- outcome/success/error boolean;
- provider and model;
- tool name;
- SHA-256 hashes of run, call and session identifiers.

Never record:

- prompt or system prompt;
- model response content;
- tool parameters;
- tool result content;
- headers, tokens, passwords or API keys;
- raw session, run, call or user identifiers.

Rotate the local telemetry file when it reaches the configured size. Telemetry is runtime state and must not be committed to GitHub.

## 8. Build and validation gates

Before installation:

1. copy the package to a temporary directory;
2. install only package build dependencies in that temporary directory;
3. link the existing global OpenClaw package for SDK resolution;
4. run TypeScript compilation;
5. run unit tests;
6. run `openclaw plugins validate`;
7. inspect the built entry and manifest;
8. run secret and forbidden-write checks;
9. confirm OpenClaw config hash, service PID, product repository and queue remain unchanged;
10. commit only sanitized validation evidence.

No installation, config change, service restart or product task submission is allowed in this phase.

## 9. Installation phase, deferred

A later reversible installation script must:

- back up OpenClaw config;
- install the exact validated local package artifact;
- enable only the plugin entry;
- initially leave optional tools unallowed;
- restart the existing Gateway once;
- inspect plugin runtime and hook registration;
- then allow only the three read-only tools;
- smoke test tool invocation without creating a product task;
- verify rollback by removing the plugin/config entry and restoring the backup.

## 10. Commercial progression

1. v0.1: read-only tools plus latency telemetry.
2. ORIS Action API v1: registry-resolved, idempotent task submission.
3. v0.2: optional `oris_submit_task` with explicit user approval.
4. v0.3: cancel/retry/evidence actions with lifecycle authorization.
5. observability: TTFT, model duration, tool duration and end-to-end turn duration dashboards and SLOs.
