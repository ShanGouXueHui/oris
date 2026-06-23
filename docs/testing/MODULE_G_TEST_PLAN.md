# Module G Test Plan - End-to-End Runtime Harness and Acceptance Runner

## Scope

Validate deterministic end-to-end Runtime v2 scenarios that combine persistent run store, worker loop, executor adapter, evidence publisher, and approval gate.

## Test Targets

1. Success scenario completes and creates an evidence index.
2. Repair scenario handles retryable failure and completes.
3. Approval scenario enters approval, receives approval, resumes, and completes.
4. Blocked scenario enters approval, receives rejection, and becomes blocked.
5. Acceptance summary aggregates all scenario results.
6. Evidence index integrity includes artifact hashes.

## Acceptance

Module G passes only when tests pass and evidence is written to:

- `reports/testing/module_G_test_result.json`
- `reports/testing/latest_test_result.json`
- `reports/execution/module_G_execution_report.md`
