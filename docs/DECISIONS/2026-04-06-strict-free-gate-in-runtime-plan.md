# Decision: enforce strict free verification inside runtime failover plans
Date: 2026-04-06

## Context
Strict free eligibility was already enforced in active routing.
However, runtime failover plans still allowed unverified free candidates to appear in free_fallback chains.

## Decision
1. Make runtime_plan read free_eligibility.json
2. Restrict free_fallback runtime chains to machine-verified free models only
3. Keep non-free roles unaffected

## Outcome
The free fallback execution path is now consistent with the strict free verification policy.
