# Decision: automate active model routing selection
Date: 2026-04-06

## Context
Provider catalog sync alone is insufficient.
ORIS must automatically decide which model to use per role, without manual daily intervention.

## Decision
1. Add `scripts/model_selector.py`
2. Generate `orchestration/active_routing.json` automatically
3. Chain route selection after each quota/provider probe
4. Treat `active_routing.json` as the current routing source of truth for runtime decisions

## Outcome
ORIS now has an automated decision layer on top of provider catalog sync.
Manual intervention should only happen through future override UI or exceptional risk / compliance handling.
