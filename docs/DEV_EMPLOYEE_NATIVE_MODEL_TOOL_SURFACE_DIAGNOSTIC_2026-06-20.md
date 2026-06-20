# Native Model Tool Surface Diagnostic — 2026-06-20

## Trigger evidence

Controlled retry evidence commit:

`d5cea6980ad46a51cb4f26f8e6229c11539ea2d5`

Result:

`FAILED / RuntimeError`

## Proven execution boundary

The retry passed:

- source governance;
- named automatic selftests;
- readiness and tools-denied baseline;
- Gateway and route health;
- loopback-only internal listeners;
- queue, product and ORIS source baselines;
- just-in-time private candidate dry-run;
- exact validated-config-to-backup hash equality;
- routing Skill installation and visibility to Agent `main`;
- single-scope `profile-plus-alsoAllow` activation;
- Gateway restart and health;
- exact plugin tool and typed-hook inventory;
- direct calls for all three approved ORIS tools;
- queue invariance after direct calls.

Three native Agent turns then completed successfully through Gateway transport in one persisted session. Each returned structured JSON and each model/agent lifecycle completed.

However:

- `after_tool_call = 0`;
- `model_call_ended = 3`;
- `agent_end = 3`;
- no approved tool name was reported by any turn;
- no tool duration was available;
- native Agent acceptance failed;
- rollback restored the exact tools-denied baseline and healthy Gateway.

No task, product mutation or write tool occurred.

## What the evidence proves

The failure is no longer in:

- candidate schema;
- Gateway activation;
- plugin loading;
- direct tool execution;
- routing Skill visibility;
- persisted native sessions;
- transport;
- rollback.

The remaining boundary is between the native Agent's effective model tool surface and model tool selection.

## What is not yet proven

The existing telemetry begins at `after_tool_call`. Therefore zero tool calls does not distinguish between:

1. the three ORIS tools were absent from the effective tool schema passed to the model;
2. the tools were present but the selected runtime Provider/Model did not issue tool calls;
3. the tools were present and supported, but prompt/Skill routing did not cause selection.

No further activation attempt is authorized until this distinction is made.

## New instrumentation

ORIS now extracts OpenClaw's privacy-safe `systemPromptReport.tools.entries` and `skills.entries` metadata from native Agent JSON output.

Evidence records only:

- total effective tool count;
- approved ORIS tools present;
- approved ORIS tools missing;
- whether the routing Skill is present;
- number of prompt reports observed.

It does not record:

- the system prompt;
- conversation content;
- other tool names;
- tool arguments or results;
- session identifiers;
- secrets.

The acceptance result now distinguishes:

- `approved_tools_missing_from_effective_model_surface`;
- `native_agent_telemetry_acceptance_failed` after a proven tool surface.

## Next safe action

First run the existing diagnostic-only entrypoint to verify the new parser, tests, source governance and healthy tools-denied baseline.

This diagnostic does not activate the candidate and cannot itself prove the live activated tool surface. Its purpose is to validate the instrumentation before any separately authorized inspection transaction.

A third activation attempt remains prohibited.
