# Decision: add provider scoreboard layer above probe and below route selection
Date: 2026-04-06

## Context
Probe results alone are not sufficient for long-running automatic routing.
ORIS needs an intermediate scoring layer so routing can evolve beyond pure ordered lists.

## Decision
1. Add scripts/provider_scoreboard.py
2. Generate orchestration/provider_scoreboard.json
3. Feed model scores into scripts/model_selector.py
4. Chain probe -> scoreboard -> selector in the recurring systemd job

## Outcome
ORIS now has:
- provider discovery
- provider health snapshot
- provider and model scoring
- active routing generation

This is the base required for future dynamic penalties, latency weighting, cost weighting, retry logic, and automatic failover.
