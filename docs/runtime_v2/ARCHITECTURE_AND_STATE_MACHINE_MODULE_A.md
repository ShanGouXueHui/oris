# Runtime v2 Module A - Architecture and State Machine Design

## Objective

Define ORIS Autonomous Dev Employee Runtime v2 as a persistent AI development employee runtime.

## Control Plane

OpenClaw Web is only the control plane. It submits goals, shows status, and approves high-risk actions. It must not be the long-running execution runtime.

## Execution Plane

The autonomous worker / agent loop is the execution plane. It performs planning, implementation, tests, repair, evidence writing, and GitHub commit workflow.

## Platform Boundary

ORIS contains platform runtime, governance, evidence, orchestration, state, approval, and recovery logic. Business product code must live in product repositories.

## Core Runtime Components

1. Goal intake and immutable run creation.
2. Module planner and compact context-pack generator.
3. Persistent queue and run-state store.
4. Bounded autonomous worker loop.
5. Approval gate for high-risk actions.
6. Failure classifier and repair policy.
7. Evidence writer for tests, execution reports, deployment reports, and acceptance records.
8. GitHub integration for commits, issue updates, and durable audit trail.

## State Machine

The canonical state machine is stored in:

- `schemas/runtime_v2/state_machine.schema.json`

## Failure Handling

Failure categories are stored in:

- `docs/runtime_v2/FAILURE_TAXONOMY_MODULE_A.md`

## Module A Non-Goals

- No business insight product code.
- No production deployment.
- No credential handling.
- No paid resource provisioning.
