# Decision: add local HTTP API layer above unified inference entrypoint
Date: 2026-04-06

## Context
ORIS already has a stable local script entrypoint.
A local HTTP API is needed so gateways, bots, service-account backends, and reverse proxies can call ORIS through a stable interface.

## Decision
1. Add scripts/oris_http_api.py
2. Expose:
   - GET /health
   - GET /runtime/plan
   - POST /infer
3. Keep the HTTP API local-only on 127.0.0.1
4. Let upper layers reach ORIS through this local API instead of direct script calls

## Outcome
ORIS now has a stable local HTTP API layer suitable for Nginx, OpenClaw, Feishu bridge, service-account backend, and later unified application entrypoints.
