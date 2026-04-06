# Decision: add Feishu event ingress skeleton and reply-shaping rule
Date: 2026-04-06

## Context
The bridge core was working, but exact short-answer prompts were not reliably preserved by the model output.
A more realistic Feishu integration layer is also needed above the bridge core.

## Decision
1. Add reply-shaping rule into the Feishu bridge core
2. Add scripts/feishu_event_ingress_skeleton.py
3. Support:
   - challenge payload
   - im.message.receive_v1 text event parsing
   - reply action preview generation
4. Keep real transport delivery as the next engineering layer

## Outcome
Feishu integration now has:
- executable bridge core
- executable ingress skeleton
- stricter reply control for exact short-answer requests
