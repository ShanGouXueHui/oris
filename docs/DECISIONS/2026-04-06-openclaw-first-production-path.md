# Decision: use OpenClaw as the first real production transport path
Date: 2026-04-06

## Context
ORIS already has:
- stable HTTPS v1 API
- Feishu bridge core
- Feishu ingress/transport/send skeletons

OpenClaw transport is already running in the environment and is lower-risk for first production traffic than enabling direct Feishu outbound immediately.

## Decision
1. Add scripts/openclaw_bridge_to_oris.py
2. Treat OpenClaw as the first real production transport path
3. Keep direct Feishu transport in staged / dry-run mode for now
4. Reuse ORIS v1 infer as the common backend entrypoint

## Outcome
ORIS now has a practical lower-risk path to real traffic without waiting for direct Feishu transport to be fully enabled.
