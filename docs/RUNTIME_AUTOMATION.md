# Runtime Automation

## Internal local services
ORIS HTTP API listens on loopback only:

- http://127.0.0.1:8788

This is internal-only and not intended as the external commercial entrypoint.

## External commercial HTTPS entrypoint
External access is provided through Nginx + TLS + Basic Auth on:

- https://control.orisfy.com/oris-api/v1/health
- https://control.orisfy.com/oris-api/v1/runtime/plan
- https://control.orisfy.com/oris-api/v1/infer

Current split:
- https://control.orisfy.com/ -> OpenClaw Control UI
- https://control.orisfy.com/oris-api/* -> ORIS API

## systemd user services
The service files live outside the Git repository:

- ~/.config/systemd/user/oris-quota-probe.service
- ~/.config/systemd/user/oris-http-api.service
- ~/.config/systemd/user/oris-quota-probe.timer

## Versioned external API
Current stable external contract:
- https://control.orisfy.com/oris-api/v1/health
- https://control.orisfy.com/oris-api/v1/runtime/plan
- https://control.orisfy.com/oris-api/v1/infer

## External integration rule
For current external HTTPS integrations, use Basic Auth plus X-ORIS-API-Key. This is the standard calling mode for Feishu bridge, OpenClaw bridge, and WeChat backend integration.

## Config-first rule
Non-secret runtime constants should live in repository config files first. Secrets remain in ~/.openclaw/secrets.json. Frequently adjusted business rules should move to database/admin UI later rather than staying hardcoded in scripts.
