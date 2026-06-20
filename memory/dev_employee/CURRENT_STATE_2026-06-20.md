# ORIS Dev Employee Current State — 2026-06-20

## Current task

Task id: `commercial-openclaw-readonly-tool-enable-20260618`

Status: `three_tool_native_acceptance_functionally_passed_validator_fix_pending`

Current step: `fix_telemetry_schema_outcome_contract_then_rerun_once`

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

## Model/tool boundary already resolved

Evidence commit `c415c614ac726906186da1756e3beb7c2de003b2` proved:

- Free Mesh protocol version 2 with tool calling;
- all three approved ORIS tools in native `tools.effective`;
- safe built-in model tool calling;
- ORIS Agent Harness routing;
- persisted native session correlation;
- privacy-safe telemetry;
- healthy exact rollback and final invariants.

## Latest complete three-tool acceptance

Evidence commit:

`22ee300081e98d8e2df4c3f4a495c9608db98d2b`

Reported result:

`FAILED / RuntimeError`

Passed before the validator rejection:

- source governance and automatic selftests;
- authoritative readiness and exact tools-denied baseline;
- Gateway, routes, and loopback listeners;
- queue, product, and ORIS source baselines;
- Free Mesh protocol version 2;
- candidate validation and controlled policy activation;
- routing Skill visibility;
- Plugin runtime and all four direct probes;
- queue invariance after direct probes;
- three native Agent turns through Gateway;
- one persisted native session;
- exact three-turn boundary;
- all three approved ORIS tools observed;
- no unapproved tool observed;
- telemetry content safety and file permissions.

Observed telemetry:

- `model_call_ended=6`;
- `agent_end=3`;
- `after_tool_call=4`;
- `oris_queue_status=1`;
- `oris_latest_task_status=2`;
- `oris_task_status=1`.

The only failed telemetry field was `schema_ok=false`.

Rollback succeeded:

- exact tools-denied configuration restored;
- previous marker and routing Skill restored;
- Gateway healthy;
- no product task submitted;
- no write tool added.

## Accurate root cause

The Plugin telemetry contract explicitly permits `success` and `error` boolean fields. The Python validator lists those fields in its allowed schema but then incorrectly treats `error=true` or `success=false` as malformed schema.

This mixes two independent authorities:

1. record schema validity;
2. execution outcome validity.

The second `oris_latest_task_status` attempt indicates a possible recoverable retry. A failed intermediate attempt must be counted and reported, but it must not be classified as malformed telemetry.

## Implemented correction

The correction separates telemetry analysis into:

- schema validation: JSON shape, approved keys, event types, hashes, duration and field types;
- execution outcomes: successful required tools, failed-attempt counts, retry metadata, and terminal Agent outcome.

Acceptance now requires:

- every required ORIS tool has at least one non-failed call;
- no `agent_end` record is explicitly failed;
- retries are visible but may recover;
- schema, privacy, permissions, correlation, and approved-tool-only rules still pass.

Regression tests cover:

- failed attempt followed by successful retry;
- required tool with no successful attempt;
- explicitly failed Agent completion;
- `success=false` and `error=true` remaining valid schema fields.

No Plugin change, OpenClaw reinstall, provider/model change, or policy broadening is required.

## Current runtime state

After rollback:

- exact tools-denied configuration active;
- previous marker and Skill state restored;
- Gateway and Free Mesh healthy;
- queue and product unchanged;
- internal listeners loopback-only;
- write tools absent.

## Next action

After the exact correction commit passes unified code-first audit and is merged, run once:

`scripts/dev_employee_enable_openclaw_readonly_tools.sh`

On success:

- retain the validated read-only policy, routing Skill, and private marker;
- persist read-only P0 completion;
- establish the privacy-safe model/tool/Agent latency baseline.

On failure:

- restore the exact tools-denied baseline;
- publish sanitized evidence;
- do not rerun before evidence review.

## Commercial sequence

1. complete and persist native read-only P0;
2. establish privacy-safe real latency baselines;
3. design typed write actions with approval, RBAC, project authorization, idempotency, and audit;
4. generic onboarding and capability discovery;
5. controlled Admin management;
6. monitoring, privacy, backup, and DR;
7. multi-tenant commercial packaging.
