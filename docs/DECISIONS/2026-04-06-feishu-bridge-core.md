# Decision: add Feishu bridge core above ORIS v1 infer
Date: 2026-04-06

## Context
ORIS now has a stable v1 inference API.
Feishu integration should not directly embed orchestration details.

## Decision
1. Add a reusable bridge core:
   - scripts/bridge_feishu_to_oris.py
2. Let the bridge core:
   - accept Feishu-like text input
   - choose an ORIS role
   - call local ORIS v1 infer
   - produce reply text
   - write bridge logs
3. Keep real Feishu ingress and delivery for the next layer

## Outcome
The message-to-ORIS-to-reply core is now executable and reusable, while real Feishu transport integration remains a separate concern.
