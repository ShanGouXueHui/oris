# Decision: standardize all upstream integrations on ORIS HTTPS v1 infer endpoint
Date: 2026-04-06

## Context
ORIS now has a stable commercial HTTPS entrypoint and a versioned API contract.
Different upstream products should not each invent their own protocol.

## Decision
1. Standardize on POST /oris-api/v1/infer as the common upstream entrypoint
2. Use the same request shape across Feishu, OpenClaw, and WeChat service-account backend
3. Use Basic Auth + X-ORIS-API-Key for current external HTTPS integration
4. Keep role selection as the main routing control surface

## Outcome
ORIS now has a unified upstream integration standard, reducing adapter complexity and future maintenance cost.
