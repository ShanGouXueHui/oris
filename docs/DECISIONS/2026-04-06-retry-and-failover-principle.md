# Decision: add retry-first and failover-second runtime principle
Date: 2026-04-06

## Context
End users should not feel provider instability directly.
If a provider or model fails transiently, ORIS should retry automatically.
If retry still fails, ORIS should switch to the next eligible model automatically.

## Decision
Runtime behavior should move toward:
1. first attempt on selected active route
2. automatic retry on transient failure
3. automatic failover to next eligible route if retry still fails
4. only surface errors to operators after automatic recovery paths are exhausted

## Product principle
This should be automatic by default.
Human intervention should only happen for:
- compliance or regulatory constraints
- repeated abnormal failures
- explicit operator override through UI in the future
