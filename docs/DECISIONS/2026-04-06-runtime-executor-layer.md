# Decision: add runtime executor layer
Date: 2026-04-06

## Context
Planning alone is not enough.
ORIS needs a runtime executor that can actually perform:
- execution_primary call
- retry
- failover
- runtime feedback writeback

## Decision
1. Add scripts/runtime_execute.py
2. Read orchestration/runtime_plan.json
3. Execute execution_primary first
4. Retry according to role runtime policy
5. Fail over to the next eligible model automatically
6. Write success/failure back through scripts/runtime_feedback.py

## Outcome
ORIS now has an executable runtime layer rather than planning-only orchestration.
