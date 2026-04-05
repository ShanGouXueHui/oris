# Decision: add runtime plan layer for retry-first and failover-second execution
Date: 2026-04-06

## Context
Scoring and active routing are not enough for user-facing resilience.
ORIS also needs a runtime execution plan so transient failures can be retried automatically and persistent failures can fail over automatically.

## Decision
1. Add scripts/runtime_plan.py
2. Generate orchestration/runtime_plan.json
3. Generate retry and failover chains per role
4. Chain runtime planning after probe, scoring, and route selection

## Outcome
ORIS now has a runtime execution-planning layer that can support:
- retry-first execution
- failover-second execution
- future model penalty and blocking logic
