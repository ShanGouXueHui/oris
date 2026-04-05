# Decision: successful runtime feedback clears temporary block and restores eligibility
Date: 2026-04-06

## Context
ORIS already supports temporary blocking after repeated failures.
The remaining validation step is to confirm that one successful execution clears the block and restores the model into runtime eligibility.

## Validation
Model tested:
- qwen3.6-plus

Expected behavior:
1. consecutive_failures resets to 0
2. blocked_until clears to null
3. cn_candidate_pool execution_primary returns to qwen3.6-plus
4. unrelated roles such as free_fallback remain unaffected

## Outcome
The temporary block mechanism is reversible.
ORIS can now both:
- fail away from unstable models
- restore recovered models automatically after success
