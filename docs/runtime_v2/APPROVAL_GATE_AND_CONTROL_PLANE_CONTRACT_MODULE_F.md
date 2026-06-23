# Runtime v2 Module F - Approval Gate and Control Plane Contract

## Objective

Module F formalizes the OpenClaw Web control-plane boundary for high-risk actions while keeping the autonomous worker as the execution runtime.

## Approval Request Contract

Approval requests capture:

- approval id;
- run id;
- status;
- risk level;
- action type;
- reason;
- evidence reference;
- timestamps.

The schema is stored in `schemas/runtime_v2/approval_request.schema.json`.

## Approval Decision Contract

Decisions are explicit and auditable:

- `APPROVE`
- `REJECT`
- `EXPIRE`

The schema is stored in `schemas/runtime_v2/approval_decision.schema.json`.

## State Mapping

- `APPROVE`: `WAITING_APPROVAL -> RUNNING`
- `REJECT`: `WAITING_APPROVAL -> FAILED_BLOCKED`
- `EXPIRE`: `WAITING_APPROVAL -> FAILED_BLOCKED`

Duplicate decisions are idempotent: once a request is no longer pending, later decisions return the existing state without mutating it.

## Control Plane Boundary

OpenClaw Web may create or resolve approval decisions. It does not become the long-running execution runtime.

## Non-Goals

- No web UI implementation.
- No production auth/RBAC.
- No product repository mutation.
- No deployment workflow.
