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

### 3. Transport skeleton
File:
- scripts/feishu_transport_skeleton.py

Responsibility:
- add event idempotency / dedupe
- call ingress skeleton
- convert reply preview into Feishu send envelope
- output transport preview object
- write transport log

### 4. Send executor skeleton
File:
- scripts/feishu_send_executor_skeleton.py

Responsibility:
- fetch tenant_access_token
- convert send envelope into Feishu API request
- support dry-run preview
- support real execution when explicitly enabled
- skip deduped inputs safely
- write send executor log

### 5. Worker skeleton
File:
- scripts/feishu_worker_skeleton.py

Responsibility:
- chain transport skeleton and send executor skeleton
- stop safely on challenge / deduped mode
- produce one combined worker result

## Logs
- orchestration/bridge_feishu_log.jsonl
- orchestration/feishu_event_ingress_log.jsonl
- orchestration/feishu_transport_log.jsonl
- orchestration/feishu_send_executor_log.jsonl

## Dedupe store
- orchestration/feishu_event_dedupe.json

## Current status
Feishu integration now has:
- bridge core
- event ingress skeleton
- transport skeleton
- send executor skeleton
- worker skeleton

## Next step
The next layer should connect the worker skeleton to a real inbound server path and decide when to enable execute-send in production.
