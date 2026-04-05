# Runtime Automation

## Internal local services
ORIS HTTP API listens on loopback only:

- http://127.0.0.1:8788

This is internal-only and not intended as the external commercial entrypoint.

## External commercial HTTPS entrypoint
External access is provided through Nginx + TLS + Basic Auth on:

- https://control.orisfy.com/oris-api/health
- https://control.orisfy.com/oris-api/runtime/plan
- https://control.orisfy.com/oris-api/infer

Current split:
- https://control.orisfy.com/ -> OpenClaw Control UI
- https://control.orisfy.com/oris-api/* -> ORIS API

## systemd user services
The service files live outside the Git repository:

- ~/.config/systemd/user/oris-quota-probe.service
- ~/.config/systemd/user/oris-http-api.service
- ~/.config/systemd/user/oris-quota-probe.timer
