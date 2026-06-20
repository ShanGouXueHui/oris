# ORIS Dev Employee Current State — 2026-06-20

## Current task

Task id: `commercial-openclaw-readonly-tool-enable-20260618`

Status: `model_tool_call_and_oris_routing_pass_pending_three_tool_native_acceptance`

Current step: `run_three_tool_native_language_acceptance`

## Fixed commercial architecture

```text
user
  -> native OpenClaw UI and native sessions
  -> native ORIS Plugin / Agent Harness
  -> ORIS task governance and evidence
  -> Codex real code execution
  -> product commit, tests and ORIS evidence returned through OpenClaw
```

Native OpenClaw remains the commercial primary UI. The custom ORIS Web Console remains restricted diagnostics and rollback only.

Do not reinstall or upgrade OpenClaw. Do not reinstall the Plugin. Do not expose internal listeners. Do not add write tools in this task. Do not touch production host `8.136.28.6`.

## Installed baseline

- Plugin: `oris-dev-employee` `0.1.0`;
- approved read-only tools: `oris_queue_status`, `oris_task_status`, `oris_latest_task_status`;
- typed hooks: `model_call_ended`, `after_tool_call`, `agent_end`;
- readiness: `26/26 PASS`;
- active product task: none;
- product baseline: `bcb93e17ea88704548101f5e4a5c460e15a80ec7`;
- write tools: absent and unauthorized.

## Resolved effective-surface and model-capability boundary

Authoritative evidence commit:

`c415c614ac726906186da1756e3beb7c2de003b2`

Result:

`MODEL_TOOL_CALL_AND_ORIS_ROUTING_PASS`

Verified facts:

- all `26/26` checks passed;
- Free Mesh protocol version 2 was active and tool calling was enabled;
- all three approved ORIS tools were present in native `tools.effective` and plugin-owned;
- a safe built-in tool was called by the runtime model;
- `oris_queue_status` was called through the native Agent Harness;
- two approved `after_tool_call` events were correlated;
- Gateway transport and a persisted native session were proven;
- telemetry schema, permissions, content safety, and approved-tool-only checks passed;
- exact tools-denied rollback completed successfully;
- queue, product repository, and loopback listener invariants passed;
- no product task was submitted;
- no write tool was added;
- OpenClaw was not reinstalled or upgraded.

The earlier uncertainty is resolved: tools are materialized, the provider/model can issue tool calls, and ORIS Agent Harness routing works.

## Current runtime state

After the successful diagnostic rollback:

- exact tools-denied configuration restored;
- previous marker and Skill state restored;
- Gateway healthy;
- Free Mesh service healthy;
- queue unchanged;
- product repository unchanged;
- internal listeners loopback-only.

## Next authorized transaction

Run the existing complete three-tool native acceptance exactly once:

`scripts/dev_employee_enable_openclaw_readonly_tools.sh`

The transaction uses `config/dev_employee/openclaw_readonly_acceptance.json`, which defines three Chinese natural-language turns in one persisted native OpenClaw session:

1. current queue status through `oris_queue_status`;
2. latest task status through `oris_latest_task_status`;
3. current governed task status through `oris_task_status`.

Before policy mutation and model calls, the transaction must revalidate source governance, selftests, readiness, tools-denied baseline, Gateway/routes, loopback listeners, queue baseline, product baseline, ORIS source cleanliness, and Free Mesh protocol version 2.

## Passing conditions

- all three natural-language turns return successfully;
- all three expected ORIS tools appear in correlated `after_tool_call` telemetry;
- no unapproved tool appears;
- exactly three Agent turns complete in one persisted native session;
- Gateway transport is proven and embedded fallback is absent;
- telemetry privacy, schema, and permissions pass;
- queue, product, ORIS source, routes, listeners, and write-tool invariants pass;
- sanitized GitHub evidence is committed and remote-verified.

## Success and failure behavior

On success:

- result: `ENABLED_READONLY_AUTOMATIC_ACCEPTED`;
- validated read-only policy remains active;
- routing Skill and private marker remain active;
- native OpenClaw UI becomes the approved P0 read-only commercial path;
- next action: `ESTABLISH_PRIVACY_SAFE_LATENCY_BASELINE`.

On failure:

- restore exact tools-denied configuration, marker, and Skill state;
- verify Gateway, queue, product, and listener invariants;
- publish sanitized failure evidence;
- do not repeat the complete acceptance before reviewing that evidence.

## Work still not completed

- three-tool native natural-language acceptance;
- read-only P0 completion persistence;
- real privacy-safe model/tool/agent latency baseline;
- typed write actions with approval, RBAC, project authorization, idempotency, and audit;
- generic project onboarding and capability discovery;
- controlled Admin UI for Provider, Model, and Policy;
- monitoring, privacy/retention, backup/restore, and disaster recovery;
- multi-tenant identity, quotas, metering, and commercial packaging;
- production validation.

## Commercial sequence

1. complete and persist native read-only P0;
2. establish privacy-safe real latency baselines;
3. design typed write actions only after P0 passes;
4. generic onboarding and capability discovery;
5. controlled Admin management;
6. monitoring, privacy, backup, and DR;
7. multi-tenant commercial packaging.
