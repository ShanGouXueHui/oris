# Decision: add Feishu worker skeleton and deduped-send guard
Date: 2026-04-06

## Context
The send executor skeleton accepted a deduped preview without a send envelope, which produced an invalid dry-run send request.

## Decision
1. Make the send executor explicitly skip deduped inputs
2. Fail fast on missing send_envelope
3. Add scripts/feishu_worker_skeleton.py
4. Let the worker chain:
   - transport skeleton
   - send executor skeleton
5. Stop safely when the transport result is challenge or deduped

## Outcome
Feishu integration now has a safer end-to-end worker skeleton and no longer produces misleading send previews from deduped inputs.
