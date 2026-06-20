# Dev Employee Free Mesh Tool-Calling Fix — 2026-06-20

## Status

Implementation and validation authority for restoring native OpenClaw tool calling through the ORIS Free Mesh provider.

## Proven failure boundary

Evidence commit `b755ef846ce4dd13b62c3642a8ba62862a494f97` proved:

- the native Gateway effective surface contained all three approved ORIS tools;
- Plugin ownership and required hooks were correct;
- the routing Skill was visible to Agent `main`;
- a safe built-in control tool and `oris_queue_status` both produced zero `after_tool_call` events;
- Provider runtime fact was `oris`;
- Model runtime fact was `free-auto`;
- both model turns completed with structured output;
- rollback and final queue/product/listener invariants passed.

## Root cause

The Free Mesh bridge implemented only text chat compatibility:

1. OpenClaw sent requests to the local OpenAI-compatible bridge.
2. `scripts/oris_free_mesh_api.py` read `model` and `messages` only.
3. Messages were flattened into a plain prompt.
4. `tools`, `tool_choice`, assistant `tool_calls`, and `tool` role messages were discarded.
5. `scripts/runtime_execute.py` sent only text-chat payloads downstream.
6. Provider responses were reduced to `message.content` and returned with `finish_reason=stop`.

This made tool calling impossible even when OpenClaw materialized the correct effective tool surface.

## Implemented architecture

### OpenAI chat contract

`oris_vnext/openai_chat_contract.py`

- validates structured messages and function tools;
- preserves `tools`, `tool_choice`, structured tool history, and selected request options;
- rejects duplicate or unauthorized tool names;
- normalizes standard OpenAI assistant tool-call responses;
- exposes privacy-safe count-only metadata.

### Provider client

`oris_vnext/runtime_provider_client.py`

- forwards complete OpenAI-compatible requests to supported providers;
- normalizes content and tool-call responses;
- rejects unauthorized downstream tool names;
- marks provider protocols without enabled tool translation as unsupported instead of poisoning provider health.

Gemini text behavior remains supported. Gemini tool translation is intentionally fail-closed until implemented and tested.

### Execution engine

- `oris_vnext/runtime_execution_state.py`
- `oris_vnext/runtime_execution_engine.py`
- `scripts/runtime_execute.py`

The previous mixed-responsibility executor was split into:

- credentials and runtime-state management;
- provider execution;
- retry/failover orchestration;
- a thin CLI supporting either legacy `--prompt` or structured `--request-file`.

Attempts logs contain provider/model/status/error class only. They do not contain prompts, tool schemas, arguments, results, or secrets.

### Free Mesh HTTP boundary

- `oris_vnext/free_mesh_http.py`
- `oris_vnext/free_mesh_inference.py`
- `scripts/oris_free_mesh_api.py`

The HTTP bridge now:

- validates the complete chat request;
- uses a private `0600` temporary request file;
- removes the temporary file after child execution;
- returns standard OpenAI `tool_calls` and `finish_reason` values;
- records only request counts, latency, selected runtime provider/model, and tool-call count;
- never records conversation content, tool schemas, args/results, or authentication values.

### Capability-aware logical routing

Tool-bearing requests are assigned to the logical `tool_calling` role. The role is configured in:

- `orchestration/routing_policy.yaml`;
- `orchestration/runtime_policy.yaml`.

The role does not hardcode a single provider/model in execution code. Existing health, free eligibility, score, block, retry, and failover mechanisms continue to choose runtime candidates.

`oris_vnext/infer_refresh.py` forces routing refresh when the required role is missing, even when old artifacts are still within TTL.

## Safety invariants

- no product task submission;
- no write tool addition;
- no broad prompt-keyword task creation;
- provider/model identities remain runtime facts;
- tools are restricted to function tools supplied by OpenClaw;
- downstream tool calls must use an authorized tool name;
- tool arguments/results are transported only in private process memory or private temporary files;
- conversation content and tool data are absent from evidence and latency logs;
- OpenClaw installation/version is unchanged;
- production machine `8.136.28.6` is not touched.

## Required validation order

1. offline Python compile;
2. shell syntax;
3. pure unit tests in `tests/test_free_mesh_tool_calling.py`;
4. repository code-first audit with all findings zero;
5. merge the validated short-lived branch to `main`;
6. execute the code-first audit on the development machine and publish evidence;
7. restart only the existing Free Mesh service when required;
8. run the existing model tool-call and Agent Harness routing diagnostic;
9. inspect GitHub evidence before deciding the next action;
10. only after generic capability passes, run the full three-tool natural-language acceptance.

## Decision outcomes after runtime validation

- request metadata reports `tool_count=0`: inspect OpenClaw provider request construction;
- request metadata reports tools but no downstream tool call: inspect selected model capability and provider response;
- safe built-in control tool succeeds but ORIS tool fails: fix ORIS Skill/Harness routing;
- both succeed: proceed to full three-tool read-only native acceptance.
