# Decision: add versioned API contract and application bearer auth
Date: 2026-04-06

## Context
Commercial integrations need a stable API contract.
Basic Auth at the reverse proxy is not sufficient as the long-term application-layer authentication mechanism.

## Decision
1. Add versioned endpoints:
   - GET /v1/health
   - GET /v1/runtime/plan
   - POST /v1/infer
2. Add application-layer bearer authentication
3. Keep legacy endpoints for backward compatibility
4. Preserve HTTPS as the only external commercial entrypoint

## Outcome
ORIS now has a stable versioned API contract suitable for service-account backend, Feishu bridge, OpenClaw integration, and future front-end applications.
