# Module B Test Plan - Persistent Run Store and Queue Contract

## Scope

Validate the minimal durable Runtime v2 substrate for run records, queue items, state transitions, and append-only events.

## Test Targets

1. Run records persist across store reloads.
2. Idempotent run creation returns the existing run for the same key.
3. Queue items persist and can be claimed exactly once.
4. State transitions follow the Module A state machine.
5. Terminal states reject further transitions.
6. Event records are append-only and survive reload.

## Acceptance

Module B passes only when tests pass and evidence is written to:

- `reports/testing/module_B_test_result.json`
- `reports/testing/latest_test_result.json`
- `reports/execution/module_B_execution_report.md`
