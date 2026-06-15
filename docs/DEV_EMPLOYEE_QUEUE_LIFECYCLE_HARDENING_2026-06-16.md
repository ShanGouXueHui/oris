# ORIS Dev Employee Queue & Lifecycle Hardening — 2026-06-16

## 1. Scope

This document defines commercial hardening phase P1-A after the successful full-chain acceptance.

The goal is not to rerun the acceptance project. The goal is to make task ownership and lifecycle control safe enough for repeated commercial use while the operational store is still filesystem-backed.

## 2. Safety doctrine

1. A task is claimed exactly once by an atomic queue transition and a per-task claim lock.
2. A running task is owned by a renewable lease with worker identity, PID, heartbeat, lease expiry, and execution deadline.
3. Worker loss never causes an automatic duplicate execution.
4. Lease expiry becomes terminal `failed` with `failure_code=lease_expired`.
5. Retry is explicit and creates a new Task ID with lineage and bounded attempts.
6. Cancellation is terminal for queued work and cooperative/rollback-safe for running work.
7. Cancellation closes before product commit/push.
8. Product mutation starts only from a clean local/remote baseline.
9. Cancellation, timeout, or pre-delivery execution failure rolls product files back to the verified baseline.
10. Every lifecycle mutation writes an append-only event record.

## 3. Components

### 3.1 `scripts/dev_employee_queue_kernel.py`

Authoritative filesystem transaction layer:

- atomic JSON writes with fsync and replace;
- canonical queue paths;
- per-task claim locks;
- lease and heartbeat fields;
- cancellation control records;
- append-only JSONL event ledger;
- idempotency fingerprints;
- retry Task ID allocation;
- safe lease expiry.

The data model is intentionally compatible with a future database-backed task/event ledger.

### 3.2 `scripts/dev_employee_supervised_bridge_v3.py`

Runtime executor adapter:

- uses the queue kernel for claim ownership;
- enforces configurable worker concurrency slots;
- performs Codex auth preflight;
- records a clean product baseline before execution;
- renews lease while Codex runs;
- checks cancellation and execution deadline;
- terminates Codex on cancellation/timeout;
- rolls product changes back before terminal cancellation/failure;
- reuses the already-validated v2 result, test, Git, and evidence functions.

Default runtime policy:

- max concurrency: `1`;
- lease: `60` seconds;
- heartbeat: `10` seconds;
- execution timeout: `7200` seconds.

These values are host configuration, not hardcoded business policy.

### 3.3 `scripts/dev_employee_intake_api_v2.py`

Loopback control plane:

- task-id idempotency and request fingerprint conflicts;
- accepted/validated/queued events;
- lifecycle, lease, cancellation, and retry metadata in status;
- authenticated `POST /goals/{task_id}/cancel`;
- authenticated `POST /goals/{task_id}/retry`;
- bounded retry attempts and retry lineage;
- no shell execution or product mutation.

### 3.4 `scripts/dev_employee_web_console_v2.py`

Thin authenticated UI/proxy:

- submits through intake v2;
- displays lifecycle status;
- exposes Cancel and Retry controls;
- writes sanitized audit events;
- does not mutate queue files directly.

### 3.5 `scripts/dev_employee_recover_stale_tasks.py`

Safe recovery policy:

- reconciles a stale running descriptor when durable task-run evidence is already terminal;
- otherwise expires a dead lease to terminal failure;
- never automatically requeues a stale task.

## 4. Canonical lifecycle

Active:

- `accepted`
- `validated`
- `queued`
- `claimed`
- `planning`
- `executing`
- `local_checks_passed`
- `committing`
- `pushing`
- `cancelling`

Terminal:

- `completed`
- `preflight_failed`
- `local_checks_failed`
- `remote_verification_failed`
- `blocked`
- `cancelled`
- `failed`
- `error`

Detailed legacy/runtime values remain observable but map to the canonical states.

## 5. Cancellation contract

### Queued task

The queue kernel atomically changes the task to `<task_id>.cancelled.json`. The bridge cannot claim it afterward.

### Running task before commit

The control plane writes `<task_id>.cancel.json`. Bridge v3 observes it during heartbeat, terminates the executor, resets the product repository to the clean baseline, removes task-created untracked files, writes cancellation evidence, and releases the lease.

### Committing or pushing

Cancellation is rejected with HTTP 409. Delivery is allowed to finish so that local and remote repository states remain coherent.

## 6. Retry contract

- only terminal tasks can be retried;
- each retry uses a new Task ID such as `<task_id>-r1`;
- a double-click while an existing retry is active returns the same retry task;
- attempts are bounded, defaulting to 3;
- the original task remains immutable and auditable;
- no automatic retry follows lease expiry or executor failure.

## 7. Deployment gate

Before switching services to v2/v3:

- no `*.running.json` task may exist;
- no `*.queued.json` task may exist unless deliberately approved for migration;
- all standard-library tests and Python compilation must pass;
- current completed-task status/evidence must remain readable.

## 8. Server-side acceptance

Required before browser testing:

1. unit tests for task states, queue kernel, intake v2, Web Console v2, and Codex auth preflight;
2. service overrides installed and daemon reloaded;
3. intake v2 health returns 200;
4. Web Console v2 health returns 200;
5. unauthenticated intake mutation returns 401;
6. prior completed final-acceptance task still returns terminal completed with evidence;
7. bridge v3 is active and owns one concurrency slot;
8. stale recovery dry execution produces no automatic requeue.

No real product task is submitted during this deployment acceptance.

## 9. Browser acceptance

After server-side acceptance passes, the operator logs into `https://control.orisfy.com` and verifies:

- project list and completed-task status still load;
- lifecycle fields are visible;
- Cancel and Retry buttons are present;
- a dedicated no-product-change lifecycle test task can be cancelled while queued;
- retry of that cancelled task creates a new Task ID exactly once.

Browser acceptance must not reuse the completed final-acceptance task.

## 10. Next phase

P1-B follows only after P1-A is stable:

- database-backed task/event store;
- distributed workers and database leases;
- tenant/project concurrency quotas;
- resumable delivery stages;
- Admin UI for retry/cancel policy and worker health;
- metrics and SLO alerts.
