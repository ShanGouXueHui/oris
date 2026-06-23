# Module E Test Plan - GitHub Evidence Publisher and Run Evidence Index

## Scope

Validate deterministic evidence aggregation and publish-plan generation so ORIS progress can be audited from GitHub without relying on chat history or long terminal logs.

## Test Targets

1. Evidence artifacts are hashed and captured in an evidence index.
2. Missing artifacts are rejected before publishing.
3. Evidence index IDs are deterministic for the same module and artifact set.
4. Publish plans include branch, commit message, files, and evidence index reference.
5. GitHub issue update payloads summarize module status and evidence paths.
6. Executor/worker evidence artifacts can be aggregated into the index.

## Acceptance

Module E passes only when tests pass and evidence is written to:

- `reports/testing/module_E_test_result.json`
- `reports/testing/latest_test_result.json`
- `reports/execution/module_E_execution_report.md`
