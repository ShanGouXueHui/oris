# Decision: expose ORIS through a commercial HTTPS entrypoint
Date: 2026-04-06

## Context
Commercial systems should use HTTPS for external interaction.
Local loopback HTTP is acceptable only for internal service-to-service communication on the host.

## Decision
1. Keep ORIS HTTP API bound to 127.0.0.1:8788
2. Expose external access only through Nginx + TLS + Basic Auth
3. Reuse control.orisfy.com as the current secure external entrypoint
4. Route:
   - / -> OpenClaw Control UI
   - /oris-api/health -> ORIS health
   - /oris-api/runtime/plan -> ORIS runtime plan
   - /oris-api/infer -> ORIS inference

## Outcome
ORIS now has a secure HTTPS external entrypoint suitable for production-style integration while preserving loopback-only internal service exposure.
