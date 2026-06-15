# Current AI Dev Employee Task

Status: implementation prepared; server-side deployment pending

Task id: `commercial-hardening-queue-lifecycle-20260616`

Target project: `oris`

Target repository: `ShanGouXueHui/oris`

Target local path: `/home/admin/projects/oris`

## Objective

Deploy the first commercial hardening slice after final acceptance:

- transaction-safe filesystem queue ownership;
- canonical lifecycle state machine;
- per-task lease and heartbeat;
- bounded execution timeout;
- cancellation with pre-delivery product rollback;
- explicit retry with new Task ID and bounded attempts;
- configurable worker concurrency;
- safe stale-task expiry without automatic re-execution;
- append-only lifecycle event ledger.

This task does not modify a product repository and does not submit a real Codex product task during deployment acceptance.

## Prepared implementation

- `scripts/dev_employee_queue_kernel.py`
- `scripts/dev_employee_supervised_bridge_v3.py`
- `scripts/dev_employee_intake_api_v2.py`
- `scripts/dev_employee_web_console_v2.py`
- `scripts/dev_employee_recover_stale_tasks.py`
- `scripts/dev_employee_task_states.py`
- standard-library regression tests under `tests/`
- `docs/DEV_EMPLOYEE_QUEUE_LIFECYCLE_HARDENING_2026-06-16.md`
- evidence-safe deployment script `scripts/dev_employee_deploy_queue_lifecycle_hardening_v2_20260616.sh`

## Key commercial policy

- worker loss does not automatically requeue or duplicate execution;
- lease expiry becomes terminal `failed` with `failure_code=lease_expired`;
- retry is explicit and creates a new Task ID;
- queued cancellation is atomic;
- running cancellation is observed by bridge heartbeat;
- cancellation/timeout before delivery resets the product repository to its verified clean baseline;
- cancellation is rejected once commit or push begins;
- default concurrency is one worker slot until quota policy is productized.

## Deployment acceptance

The deployment script must prove:

1. no queued/running task exists before service switch;
2. Python compilation and all standard-library tests pass;
3. Codex non-interactive preflight passes;
4. bridge/intake/Web services switch to v3/v2/v2 and remain active;
5. loopback health and authentication boundaries pass;
6. the completed final-acceptance task remains readable with evidence;
7. Web lifecycle controls are rendered;
8. stale recovery does not automatically requeue;
9. bridge v3 acquires one configured worker slot;
10. no real product task is submitted.

## Browser acceptance

Only after the server-side deployment returns `PASS` and `NEXT_ACTION=REQUEST_BROWSER_LIFECYCLE_TEST`:

- the operator logs into `https://control.orisfy.com`;
- verifies status and lifecycle fields;
- verifies Cancel and Retry controls;
- uses a dedicated lifecycle test task, not the completed final-acceptance task.

## Prerequisite evidence

Final commercial-chain acceptance remains complete:

- accepted task: `goal-oris-final-acceptance-api-readonly-e2e-20260616-044030`
- product SHA: `3207f20a2afdf109beac9a4a95523e7792e0ae33`
- ORIS evidence SHA: `188a17eeba4acb43f5b922560ad98c3d8d28c587`
- evidence index SHA: `4425edbe8e29912ff44d41da2a5e458bdac292d3`
- independent verification SHA: `f1bb1cfcefbd7a3b5abb2a4f3bf6b4c00707605e`

## Next action

Run the GitHub-hosted deployment script as Linux user `admin` on `43.106.55.255`. Send only the final `===== SUMMARY =====` block. Do not log into the Web Console for lifecycle testing until the server-side deployment passes.
