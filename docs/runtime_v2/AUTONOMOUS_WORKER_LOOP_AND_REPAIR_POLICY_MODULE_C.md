# Runtime v2 Module C - Autonomous Worker Loop and Repair Policy

## Objective

Module C connects the Module B persistent run store and queue contract to a bounded autonomous worker iteration.

## Worker Loop Contract

One worker iteration performs at most one queue claim and one bounded task attempt sequence:

1. claim next queued item;
2. skip terminal runs safely;
3. drive run from `RECEIVED` to `RUNNING` through valid Module A transitions;
4. execute a task executor;
5. map task outcome to success, retryable repair, approval gate, or fatal stop;
6. write append-only worker evidence events;
7. ack queue item when the worker path reaches terminal handling.

## Repair Policy

Retryable failures transition through:

```text
RUNNING -> FAILED_RETRYABLE -> REPAIRING -> TESTING
```

The worker then retries within a bounded `max_repair_attempts` budget.

## Approval Policy

Approval-required outcomes transition to `WAITING_APPROVAL` and do not auto-complete. This represents the OpenClaw Web control-plane approval boundary.

## Fatal Policy

Fatal outcomes are converted to a safe terminal stop using existing Module A transitions. The worker records `WORKER_FATAL_FAILURE` evidence.

## Evidence Policy

Worker decisions are appended to the persistent event log. Long execution logs are written to `reports/execution/`; concise test results are written to `reports/testing/`.

## Non-Goals

- No real Codex execution yet.
- No production deployment.
- No product repository mutation.
- No approval UI implementation yet.
