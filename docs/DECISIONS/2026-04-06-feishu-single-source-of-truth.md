# Decision: unify real Feishu ingress with bridge single source of truth
Date: 2026-04-06

## Context
Local bridge smoke tests had the new response governance, but real Feishu inbound behavior still exposed old reply behavior.
This indicated that production ingress and local smoke paths were not fully unified.

## Decision
1. Make `scripts/feishu_event_ingress_skeleton.py` call `scripts/bridge_feishu_to_oris.py`
2. Treat `bridge_feishu_to_oris.py` as the single source of truth for:
   - task-based role selection
   - meta-question policy
   - exact short-reply rule
   - unsafe output guard
3. Remove reply-policy drift between smoke path and real production ingress path

## Outcome
Real Feishu inbound messages and local bridge tests now share the same response-governance path.
