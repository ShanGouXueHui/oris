# Decision: add failure memory and block-aware execution primary
Date: 2026-04-06

## Context
Runtime planning without failure memory is not enough for resilient user-facing execution.
ORIS must remember repeated failures, temporarily block unstable models, and automatically switch execution to the next healthy candidate.

## Decision
1. Add scripts/runtime_feedback.py
2. Store per-model runtime failure memory in orchestration/runtime_state.json
3. Block models temporarily after consecutive failures exceed threshold
4. Keep selected_model for routing truth, but add execution_primary for actual runtime execution
5. If selected_model is blocked, execution_primary must automatically switch to the next eligible model

## Outcome
ORIS now supports:
- consecutive failure tracking
- temporary blocking
- block-aware failover execution
- user-facing retry-first and failover-second behavior
