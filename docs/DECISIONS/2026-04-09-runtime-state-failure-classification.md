# Decision: classify execution failures into runtime state for routing governance

## Date
2026-04-09

## Context
After free routing auto-refresh was stabilized, ORIS still needed a clearer runtime governance layer for failures.
The goal was to avoid treating all failures as generic errors, and instead convert them into structured routing signals.

## Final implementation
`runtime_execute.py` now classifies failures into:
- `missing_key`
- `priced_out`
- `rate_limited`
- `provider_unstable`
- `execution_error`

These classifications are written back into `orchestration/runtime_state.json` at model level, together with:
- `last_error_class`
- `last_provider_id`
- `blocked_until`
- `last_failure_at`
- `last_success_at`
- `consecutive_failures`

## Verified result
Classification test confirmed:
- `missing_api_key -> missing_key`
- `402 -> priced_out`
- `429 -> rate_limited`
- `503 -> provider_unstable`
- generic runtime error -> execution_error`

Mainline smoke still succeeds:
- `report_generation -> qwen3.6-plus -> alibaba_bailian`

## Impact
This upgrades ORIS free model routing from pure refresh-and-execute into refresh-execute-governance.
Future routing can consume these runtime state signals for more stable failover and recovery.
