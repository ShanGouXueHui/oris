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
- `orchestration/active_routing.json`
- `scripts/quota_probe.py`
- `scripts/model_selector.py`

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
This module now auto-refreshes the OpenRouter catalog through the OpenRouter Models API and writes runtime snapshots automatically.
The provider registry should be treated as an auto-generated cache, not as a hand-maintained source of truth.
Manual work should be limited to routing policy and rare overrides.

## Decision layer
The orchestration stack now includes an automatic selector that writes `orchestration/active_routing.json`.
This file should be treated as the current routing source of truth.
