# Decision: add Feishu transport skeleton with idempotency preview
Date: 2026-04-06

## Context
Feishu bridge core and ingress skeleton were already working.
Before adding real outbound delivery, ORIS needs a transport-level preview layer with event deduplication and send-envelope generation.

## Decision
1. Add scripts/feishu_transport_skeleton.py
2. Add orchestration/feishu_event_dedupe.json
3. Support:
   - event/message identity extraction
   - dedupe check
   - ingress execution
   - Feishu send-envelope preview
4. Keep real outbound send execution for the next layer

## Outcome
Feishu integration now has a transport-level skeleton suitable for safe progression toward real webhook handling and outbound delivery.
