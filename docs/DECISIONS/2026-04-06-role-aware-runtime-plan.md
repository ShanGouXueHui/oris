# Decision: make runtime failover chains role-aware
Date: 2026-04-06

## Context
A generic score-only failover chain can place coder-oriented models too high for non-coding roles.
Runtime plans need role affinity so failover chains remain semantically appropriate.

## Decision
1. Add role-affinity adjustment into runtime planning
2. Prefer coder models for coding roles
3. Penalize coder models in general/report roles
4. Prefer CN providers inside cn_candidate_pool

## Outcome
Runtime failover chains are now more aligned with real task semantics instead of pure model score ordering.
