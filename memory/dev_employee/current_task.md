# Current AI Dev Employee Task

Status: `three_tool_native_acceptance_functionally_passed_validator_fix_pending`

Task id: `commercial-openclaw-readonly-tool-enable-20260618`

Current step: `fix_telemetry_schema_outcome_contract_then_rerun_once`

## Latest complete acceptance evidence

Evidence commit:

`22ee300081e98d8e2df4c3f4a495c9608db98d2b`

Reported result:

`FAILED / RuntimeError`

The runtime path itself completed successfully:

- Free Mesh protocol version 2 passed;
- direct calls to all three ORIS tools passed;
- three native Agent turns returned zero through Gateway;
- one persisted native session was proven;
- `model_call_ended=6`;
- `agent_end=3`;
- `after_tool_call=4`;
- all three required tools were observed;
- no unapproved tool was observed;
- exact three-turn boundary passed;
- telemetry content safety and file permissions passed;
- rollback restored the exact tools-denied baseline;
- no product task or write tool was introduced.

Tool attempts were:

- `oris_queue_status`: 1;
- `oris_latest_task_status`: 2;
- `oris_task_status`: 1.

## Accurate failure boundary

The only failed telemetry field was:

`schema_ok=false`

The Plugin contract explicitly permits `success` and `error` boolean fields. The validator also lists those fields in its allowed schema, but then incorrectly marks any `error=true` or `success=false` record as a schema violation.

This conflates two separate concerns:

1. whether a telemetry record has an approved structure;
2. whether an individual model, tool, or Agent attempt reported failure.

The duplicate latest-task call indicates a possible recoverable retry. A recoverable attempt must be counted and surfaced, but it must not be mislabeled as malformed telemetry.

## Required correction

Separate telemetry schema validation from execution-outcome validation.

Schema validation must continue to reject:

- malformed JSON;
- non-object records;
- unknown or forbidden fields;
- unexpected hook types;
- invalid hashes;
- invalid duration values.

Execution-outcome validation must:

- require at least one non-failed call for every approved ORIS tool;
- reject any explicitly failed `agent_end` record;
- retain failed-attempt counts and retry metadata;
- permit a failed intermediate attempt only when the required tool later succeeds and the Agent turn completes successfully.

No Plugin modification, OpenClaw reinstall, provider/model change, or policy broadening is required.

## Current runtime state

The failed transaction rolled back successfully:

- exact tools-denied configuration restored;
- previous marker and routing Skill state restored;
- Gateway healthy;
- queue and product unchanged;
- write tools absent.

## Next required action

1. merge the telemetry schema/outcome correction only after the exact branch passes the unified code-first audit;
2. rerun the existing complete acceptance exactly once:

`scripts/dev_employee_enable_openclaw_readonly_tools.sh`

On success, retain the validated read-only policy and routing Skill and proceed to P0 completion persistence plus the privacy-safe latency baseline.

## Prohibitions

- no write tools or typed write actions in this task;
- no product task submission;
- no OpenClaw reinstall or upgrade;
- no provider/model hardcoding;
- no public exposure of ports `18891` or `18892`;
- do not touch production host `8.136.28.6`.
