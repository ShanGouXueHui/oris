# Config Governance

## Rule hierarchy

### 1. Secrets
Sensitive values must not be hardcoded in repository code or non-secret config files.

Current secret store:
- ~/.openclaw/secrets.json

Examples:
- ORIS API bearer token
- provider API keys
- channel app secrets

### 2. Non-secret runtime constants
Non-secret runtime constants should live in repository config files first.

Current config file:
- config/bridge_runtime.json

Examples:
- local service URLs
- log paths
- dedupe paths
- default source names
- channel API URLs
- role-routing keyword sets
- reply-shaping regex patterns

### 3. Frequently adjusted operational rules
Rules that are expected to change often should move out of static files later.

Target destinations:
- database
- admin UI
- operational control plane

Examples:
- routing keyword tuning
- reply policy tuning
- bridge routing overrides
- channel behavior toggles

## Coding rule
When adding new bridge/runtime code:
1. do not introduce new hardcoded non-secret constants into scripts unless there is a compelling standard-library-level reason
2. prefer config/bridge_runtime.json first
3. prefer secrets.json for sensitive values
4. prefer database/admin UI later for frequently adjusted rules

## Execution rule
Scripts must remain compatible with direct execution from project root, for example:
- python3 scripts/openclaw_bridge_to_oris.py
- python3 scripts/bridge_feishu_to_oris.py
