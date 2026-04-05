# Provider Orchestration Module

## Goal
Build a provider orchestration layer for ORIS that can:
- track free and low-cost model sources
- probe model availability and quota status
- route by role (`general`, `report`, `coding`, `fallback`)
- replace degraded or expiring free candidates automatically

## Files
- `orchestration/provider_registry.json`
- `orchestration/routing_policy.yaml`
- `orchestration/provider_health_snapshot.json`
- `scripts/quota_probe.py`

## Design principles
1. Do not hardcode promotional free-policy assumptions as permanent truth.
2. Separate:
   - provider registry
   - routing policy
   - runtime health snapshot
3. Prefer SecretRef-managed credentials.
4. Treat provider marketing promises and runtime availability as different things.
5. Keep model replacement policy machine-readable.

## Current phase
This is only the skeleton.
Actual provider probes and dynamic health logic still need implementation.
