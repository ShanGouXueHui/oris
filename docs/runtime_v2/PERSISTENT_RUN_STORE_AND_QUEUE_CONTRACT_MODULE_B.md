# Runtime v2 Module B - Persistent Run Store and Queue Contract

## Objective

Module B converts Module A's state-machine design into a minimal durable runtime substrate that can store runs, queue work, validate state transitions, and retain an append-only event trail.

## Runtime Store

The implementation is `scripts/lib/runtime_v2_run_store.py`.

The store persists a JSON document with three sections:

- `runs`: run records keyed by `run_id`;
- `queue`: queue items keyed by `queue_id`;
- `events`: append-only event records.

Writes are atomic at file level via temp-file write followed by replace.

## Run Record Contract

Run records are described in `schemas/runtime_v2/run_record.schema.json`.

A run starts in `RECEIVED` and may transition only through Module A's canonical state machine in `schemas/runtime_v2/state_machine.schema.json`.

## Queue Contract

Queue items are described in `schemas/runtime_v2/queue_item.schema.json`.

Queue statuses are:

- `QUEUED`
- `CLAIMED`
- `ACKED`
- `DEAD`

`claim_next(worker_id)` claims the highest-priority queued item exactly once.

## Idempotency

`create_run(..., idempotency_key=...)` returns the existing run for the same idempotency key.

`enqueue(..., idempotency_key=...)` returns the existing queue item for the same idempotency key.

## Recovery Semantics

A worker can recover state by loading the durable store file and reading:

- latest run state;
- queue item status;
- append-only event sequence.

## Non-Goals

- No production database yet.
- No distributed locking yet.
- No product repository mutation.
- No deployment workflow.
