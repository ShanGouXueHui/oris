# Decision: cut over Feishu to ORIS direct webhook server
Date: 2026-04-06

## Context
The project no longer requires a dry-run-only Feishu direct path before launch.

## Decision
1. Enable a real Feishu callback server
2. Enable real send execution through the worker path by default
3. Expose the public HTTPS callback route:
   - /oris-api/v1/feishu/events
4. Expose the public HTTPS health route:
   - /oris-api/v1/feishu/health
5. Keep configuration externalized:
   - secrets in ~/.openclaw/secrets.json
   - non-secret runtime constants in config/bridge_runtime.json

## Outcome
ORIS now has a direct Feishu webhook path that is ready for real inbound events and real outbound replies.
