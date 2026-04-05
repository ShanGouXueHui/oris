# Decision: cut over to v1-only API contract
Date: 2026-04-06

## Context
This is a new system and does not need long-term legacy compatibility.
Maintaining old non-versioned routes adds unnecessary complexity and future ambiguity.

## Decision
1. Remove legacy external API routes from the stable contract
2. Keep only:
   - GET /v1/health
   - GET /v1/runtime/plan
   - POST /v1/infer
3. Rotate the application bearer token after it was exposed in interactive output
4. Keep HTTPS as the only external commercial entrypoint

## Outcome
ORIS now exposes a simpler, versioned, production-oriented API surface.
