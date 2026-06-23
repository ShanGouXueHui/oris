# Module F Test Plan - Approval Gate and Control Plane Contract

## Scope

Validate the control-plane approval boundary for high-risk runtime actions while keeping OpenClaw Web outside the long-running execution path.

## Test Targets

1. Approval requests are created from runs and high-risk action metadata.
2. Approve decisions transition runs from `WAITING_APPROVAL` back to `RUNNING`.
3. Reject decisions transition runs to `FAILED_BLOCKED`.
4. Expired approvals transition runs to `FAILED_BLOCKED`.
5. Duplicate decisions are idempotent and do not mutate final decision state.
6. Approval issue payloads summarize requested action and evidence reference.
7. Worker/executor approval outcome can be converted into a pending approval request.

## Acceptance

Module F passes only when tests pass and evidence is written to:

- `reports/testing/module_F_test_result.json`
- `reports/testing/latest_test_result.json`
- `reports/execution/module_F_execution_report.md`
