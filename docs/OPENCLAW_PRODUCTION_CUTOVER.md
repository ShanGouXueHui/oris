# OpenClaw Production Cutover Checklist

## Target position
OpenClaw is the first real production transport path into ORIS.

## Current backend path
OpenClaw bridge:
- scripts/openclaw_bridge_to_oris.py

ORIS infer entrypoint:
- local: http://127.0.0.1:8788/v1/infer
- external: https://control.orisfy.com/oris-api/v1/infer

## Current status
Done:
- ORIS v1 HTTPS contract
- Basic Auth + X-ORIS-API-Key external contract
- OpenClaw bridge core
- reply exact-shaping rule
- config-first runtime refactor
- direct script execution compatibility restored

Not yet enabled:
- direct Feishu real outbound production send
- full worker production orchestration for Feishu transport

## Production choice
Phase 1:
- enable real traffic through OpenClaw path first
- keep direct Feishu transport in dry-run/staged mode

## Smoke checks before production usage
1. local ORIS health
2. HTTPS ORIS health
3. OpenClaw bridge exact-reply smoke test
4. routing/runtime plan read check
5. confirm current bearer token exists only in secrets

## Change-control rule
Before adding any new bridge/runtime script:
- decide whether constants belong in config/bridge_runtime.json
- decide whether values belong in secrets.json
- do not add new hardcoded operational constants by default

## Rollback principle
If bridge/runtime behavior regresses:
1. keep ORIS HTTPS v1 API as stable backend
2. roll back bridge script commit only
3. do not change secrets structure unless necessary
