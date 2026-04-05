# Decision: add unified inference entrypoint
Date: 2026-04-06

## Context
ORIS already has:
- routing
- scoring
- runtime plan
- runtime execution
- runtime feedback

A stable upper-layer entrypoint is still needed so callers do not need to know internal orchestration details.

## Decision
1. Add scripts/oris_infer.py
2. Use it as the stable local entrypoint for role + prompt inference
3. Refresh runtime plan before execution
4. Execute through runtime_execute.py
5. Refresh runtime plan again after feedback is written
6. Append compact request records into orchestration/execution_log.jsonl

## Outcome
Upper-layer callers can now use a single entrypoint while ORIS continues to manage routing, retry, failover, feedback, and state updates internally.
