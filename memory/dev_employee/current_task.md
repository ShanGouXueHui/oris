# Current AI Dev Employee Task

Status: `model_tool_call_and_oris_routing_pass_pending_three_tool_native_acceptance`

Task id: `commercial-openclaw-readonly-tool-enable-20260618`

Current step: `run_three_tool_native_language_acceptance`

## Objective

Complete the existing native OpenClaw read-only acceptance for all three approved ORIS tools without adding write capability or submitting a product task:

- `oris_queue_status`;
- `oris_latest_task_status`;
- `oris_task_status`.

## Proven current boundary

Sanitized evidence commit:

`c415c614ac726906186da1756e3beb7c2de003b2`

Result:

`MODEL_TOOL_CALL_AND_ORIS_ROUTING_PASS`

The evidence proves:

- `26/26` checks passed;
- Free Mesh protocol version 2 was healthy with tool calling enabled;
- all three approved ORIS tools were present in the native effective surface and plugin-owned;
- a safe built-in tool was called by the runtime model;
- `oris_queue_status` was called through the native Agent Harness;
- two approved `after_tool_call` events were correlated;
- persisted native-session and telemetry privacy checks passed;
- exact tools-denied rollback completed successfully;
- queue, product repository, and listener invariants passed;
- no product task was submitted and no write tool was added.

The earlier effective-surface versus provider/model-capability boundary is resolved.

## Next required action

Run the existing complete read-only acceptance transaction once:

`scripts/dev_employee_enable_openclaw_readonly_tools.sh`

The transaction must use `config/dev_employee/openclaw_readonly_acceptance.json`, which defines three natural-language turns in one persisted native OpenClaw session.

Before policy mutation and model turns it must revalidate source governance, selftests, readiness, tools-denied baseline, Gateway/routes, loopback listeners, queue baseline, product baseline, ORIS source cleanliness, and Free Mesh protocol version 2.

## Passing conditions

- all three natural-language turns succeed;
- all three approved ORIS tools appear in correlated telemetry;
- no unapproved tool appears;
- Gateway transport and one persisted native session are proven;
- telemetry privacy, schema, and permissions pass;
- queue, product, ORIS source, routes, listeners, and write-tool invariants pass;
- sanitized GitHub evidence is committed and remote-verified.

On success, the validated read-only policy and routing Skill remain active for the native OpenClaw UI. The next action becomes `ESTABLISH_PRIVACY_SAFE_LATENCY_BASELINE`.

On failure, the existing transaction must restore the exact tools-denied configuration, marker, and routing Skill state and publish failure evidence. Do not repeat the complete acceptance before reviewing that evidence.

## Prohibitions

- no write tools or typed write actions in this task;
- no product task submission;
- no OpenClaw reinstall or upgrade;
- no broad prompt-keyword task creation;
- no provider/model hardcoding;
- no public exposure of ports `18891` or `18892`;
- do not touch production host `8.136.28.6`.

## Remaining commercialization sequence

1. complete the three-tool native read-only acceptance;
2. persist read-only P0 completion state;
3. establish a real privacy-safe model/tool/agent latency baseline;
4. design typed write actions with approval, RBAC, project authorization, idempotency, and audit;
5. add generic project onboarding and capability discovery;
6. add controlled Admin UI management for Provider, Model, and Policy;
7. add monitoring, privacy/retention, backup/restore, and disaster recovery;
8. add multi-tenant identity, quotas, metering, and commercial packaging.
