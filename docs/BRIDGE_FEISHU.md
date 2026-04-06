# Feishu Bridge

## Layer split

### 1. Bridge core
File:
- scripts/bridge_feishu_to_oris.py

Responsibility:
- accept Feishu-like text input
- choose ORIS role
- call local ORIS v1 infer
- normalize reply text
- write bridge log

### 2. Event ingress skeleton
File:
- scripts/feishu_event_ingress_skeleton.py

Responsibility:
- accept Feishu callback-like payload
- handle challenge mode
- parse im.message.receive_v1 text message
- call bridge core
- produce reply action preview
- write ingress log

## Logs
- orchestration/bridge_feishu_log.jsonl
- orchestration/feishu_event_ingress_log.jsonl

## Reply shaping
The bridge now applies an exact-reply rule for prompts such as:
- 请只回答：...
- 只回答：...
- 请只回复：...
- 只回复：...
- 请只输出：...
- 只输出：...

This reduces reliance on the model following the instruction exactly.

## Next step
The next layer should connect the ingress skeleton to real Feishu transport:
- real inbound event verification
- real outbound reply delivery
- message deduplication / idempotency
