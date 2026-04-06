# Decision: ability-first routing principle for consumer chat
Date: 2026-04-06

## Context
Using "Chinese input => Chinese model pool" as a hard rule is not the right product principle.
The product succeeds only when answers are correct and useful.
Lower latency is acceptable; wrong answers are not.

## Decision
1. Restore Feishu default general routing to `primary_general`
2. Keep task-based routing:
   - coding
   - report_generation
   - free_fallback
   - cn_candidate_pool
3. Treat language only as a soft signal, not the primary router
4. Do not adopt translation-first as the default architecture
5. Hide raw backend model identity in consumer-facing meta-question replies

## Priority order
1. correctness
2. stability
3. safety
4. latency
5. cost

## Outcome
Consumer chat routing is now aligned to task quality rather than language shortcut heuristics.
