# Feishu Bridge Core

## Current status
A bridge core is now available in:

- scripts/bridge_feishu_to_oris.py

This is not yet the full Feishu event ingress layer.
It is the reusable bridge core that turns:
- Feishu text input
into
- ORIS role selection
- ORIS v1 infer call
- reply text output
- bridge log record

## Current flow
1. receive text
2. select ORIS role
3. call local ORIS v1 infer endpoint
4. return reply_text
5. append bridge log

## Current log
- orchestration/bridge_feishu_log.jsonl

## Role selection
Default auto role selection is heuristic:
- coding
- report_generation
- cn_candidate_pool
- free_fallback
- primary_general

## Next step
The next engineering layer should connect this bridge core to real Feishu event ingress and outbound reply delivery.
