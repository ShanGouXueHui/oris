# Module C Test Plan - Autonomous Worker Loop and Repair Policy

## Scope

Validate a bounded autonomous worker iteration that uses the Module B persistent run store and queue contract.

## Test Targets

1. A successful worker iteration claims one queued item and drives a run to `COMPLETED`.
2. A retryable task failure is repaired and then completed within retry budget.
3. An approval-required task enters `WAITING_APPROVAL` and leaves the queue item claimed for control-plane action.
4. A fatal task failure is recorded as `FAILED_FATAL`.
5. A terminal run is not mutated by a worker iteration.
6. Worker decisions are recorded in the append-only event log.

## Acceptance

Module C passes only when tests pass and evidence is written to:

- `reports/testing/module_C_test_result.json`
- `reports/testing/latest_test_result.json`
- `reports/execution/module_C_execution_report.md`
