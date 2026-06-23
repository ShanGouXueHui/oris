# Runtime v2 Module D - Tool Executor Adapter and Evidence Contract

## Objective

Module D connects the Module C worker loop to a safe executor abstraction without enabling unbounded generic execution.

## Executor Boundary

The executor accepts structured actions rather than arbitrary shell commands. Actions are checked against an allowlist before execution.

Default allowed actions for Module D validation are deterministic local test actions:

- `noop`
- `write_evidence`
- `fail_retryable`
- `fail_fatal`
- `require_approval`

Denied actions produce a structured denied result and evidence artifact. They are not executed.

## Evidence Contract

Every executor decision writes an evidence artifact with:

- artifact id;
- action type;
- status;
- creation timestamp;
- payload summary.

The artifact schema is stored in `schemas/runtime_v2/evidence_artifact.schema.json`.

## Result Mapping

Executor results are mapped to worker-compatible outcomes:

- `success`
- `retryable`
- `fatal`
- `approval_required`
- `denied` as fatal policy stop for the worker

## Sandbox Policy

Module D intentionally does not expose arbitrary command execution. Real Codex/tool integration must be added behind this adapter with explicit action contracts, risk classification, evidence writing, and approval gates.

## Non-Goals

- No unrestricted shell execution.
- No production deployment.
- No product repository mutation.
- No credential handling.
