# Module D Test Plan - Tool Executor Adapter and Evidence Contract

## Scope

Validate a safe executor abstraction that Module C worker logic can call without enabling unbounded generic execution.

## Test Targets

1. Allowed actions execute through a deterministic local test executor.
2. Denied actions are blocked before execution.
3. Evidence artifacts are created for executed allowed actions.
4. Retryable executor failures map to worker-compatible retryable outcomes.
5. Fatal executor failures map to worker-compatible fatal outcomes.
6. Approval-required actions map to worker-compatible approval outcomes.
7. Worker integration completes a run through the executor adapter.

## Acceptance

Module D passes only when tests pass and evidence is written to:

- `reports/testing/module_D_test_result.json`
- `reports/testing/latest_test_result.json`
- `reports/execution/module_D_execution_report.md`
