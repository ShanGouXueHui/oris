# Decision: make provider catalog refresh automatic instead of hand-maintained
Date: 2026-04-06

## Context
Provider rosters and free-model availability change too frequently for manual upkeep.
Hand-maintained provider catalogs become stale, error-prone, and operationally unsafe.

## Decision
1. Treat `provider_registry.json` as an auto-generated cache.
2. Keep `routing_policy.yaml` as the main hand-maintained control surface.
3. Auto-refresh the OpenRouter model catalog through the OpenRouter Models API.
4. Run the refresh through a user-level systemd timer on a recurring schedule.

## Outcome
ORIS no longer depends on manual provider-catalog maintenance for OpenRouter.
Future direct providers can be added to the same automated orchestration framework.
