# Decision: move bridge/runtime constants into config-first structure
Date: 2026-04-06

## Context
Bridge and transport scripts had accumulated hardcoded non-secret constants:
- local service URLs
- log paths
- dedupe paths
- default source names
- role-routing keyword sets
- reply-shaping regex patterns
- Feishu API endpoints

This would make the codebase harder to maintain over time.

## Decision
1. Add config/bridge_runtime.json
2. Add scripts/lib/runtime_config.py
3. Move non-secret runtime constants into the config file
4. Keep secrets in ~/.openclaw/secrets.json
5. Reserve database/admin-ui as the next layer for frequently adjusted operational rules

## Outcome
Bridge/runtime code now follows a config-first structure and is more maintainable for future iteration.
