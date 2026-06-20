# Current AI Dev Employee Task

Status: `readonly_p0_completed_latency_baseline_v1_persisted_typed_write_actions_design_pending`

Task id: `commercial-openclaw-typed-write-actions-20260620`

Current step: `new_chat_audit_current_main_then_reconcile_and_implement_offline_typed_write_action_foundation`

## Completed predecessor

Task:

`commercial-openclaw-readonly-tool-enable-20260618`

Result:

`ENABLED_READONLY_AUTOMATIC_ACCEPTED`

Evidence commit:

`65217d4bb81f4ac3cd8c6d917af95425d2b47529`

Checks:

- total: 26;
- pass: 26;
- fail: 0;
- not checked: 0.

## Current accepted runtime

- Plugin `oris-dev-employee` `0.1.0` remains installed.
- Routing Skill `oris-readonly-status` remains installed and visible to Agent `main`.
- Policy mode is `profile-authority-preserved+created-profile-also-allow+skill-unrestricted`.
- `oris_queue_status`, `oris_task_status` and `oris_latest_task_status` passed direct and native natural-language acceptance.
- Typed telemetry is schema-valid, privacy-safe and correlated to a persisted native session.
- Queue, product repository, ORIS source and loopback listener invariants passed.
- No rollback was required because the validated read-only policy was retained.
- No product task was submitted.
- No write tool is present or authorized.

## Initial latency baseline v1

Model duration:

- samples: 8;
- minimum: 2,661 ms;
- P50: 5,478 ms;
- maximum: 49,734 ms.

Agent total duration:

- samples: 3;
- minimum: 8,538 ms;
- P50: 9,029 ms;
- maximum: 69,134 ms.

ORIS tools:

- `oris_queue_status`: 13 ms;
- `oris_task_status`: 42 ms;
- `oris_latest_task_status`: 13–41 ms, P50 27 ms;
- native Skill hydration `read`: 92 ms.

The ORIS tools are millisecond-scale. Model and Agent orchestration dominate observed latency. This is an initial observed baseline, not an SLO or SLA. TTFT is unavailable from the approved typed hooks.

## Current task objective

Design and implement the minimum generic offline foundation for typed write actions with:

- typed action schemas;
- identity mapping;
- RBAC;
- project authorization;
- risk classification;
- immutable prepared operations;
- approval and replay protection;
- idempotency;
- atomic task/queue transaction semantics;
- cancellation;
- explicit terminal retry;
- privacy-safe audit.

Authoritative plan:

`docs/DEV_EMPLOYEE_TYPED_WRITE_ACTIONS_COMMERCIAL_PHASE_PLAN_2026-06-20.md`

## Mandatory first action

Start a new conversation and read the durable context in the order defined by:

`memory/dev_employee/CONTEXT_INDEX_ADDENDUM_2026-06-20.md`

Then run a fresh code-first audit on current `main` before modifying source or touching runtime.

The audit must cover:

- duplicate functions, classes, variables and module bindings;
- duplicate parsers, validators, policies and profile expansion;
- duplicate service, rollback, evidence and entrypoint helpers;
- competing authority;
- duplicate function bodies;
- import cycles;
- oversized mixed-responsibility modules;
- hardcoded project/path/host/port/branch/provider/model/runtime/version or acceptance special cases;
- legacy execution paths;
- config/code separation and contract errors.

Do not suppress a real defect through scanner allowlists.

## Offline implementation boundary

After the code gate passes:

1. inspect existing task, queue, project registry, authorization, idempotency, Plugin and Agent Harness implementations;
2. identify the single existing authority for each rule;
3. reconcile the write-action phase plan with existing code;
4. implement only the minimum generic offline foundation;
5. add schema, RBAC, authorization, approval, idempotency, transaction, cancellation/retry and privacy tests;
6. keep write actions unregistered and runtime-disabled;
7. publish source, tests and durable evidence through GitHub.

## Prohibitions

- no architecture redesign;
- no generic `exec`, shell or file-write tool;
- no broad prompt keyword task creation;
- no write-action registration or runtime activation in the contract-only phase;
- no real product task submission;
- no OpenClaw reinstall or upgrade;
- no provider/model hardcoding;
- no project-specific shared-code special case;
- no public exposure of ports `18891` or `18892`;
- do not touch production host `8.136.28.6`;
- do not weaken or remove the accepted read-only policy.

## Remaining commercial work

1. controlled typed write actions;
2. generic onboarding and capability discovery;
3. Admin Provider/Model/Policy management;
4. monitoring, alerts and SLOs;
5. privacy and retention enforcement;
6. backup/restore, upgrade rollback and DR;
7. multi-tenant identity and isolation;
8. quota and metering;
9. commercial packaging;
10. production validation under a separate explicit task.
