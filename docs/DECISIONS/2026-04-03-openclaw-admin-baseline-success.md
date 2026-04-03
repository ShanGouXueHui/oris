# Decision: OpenClaw baseline runs entirely under admin user
Date: 2026-04-03

## Context
Earlier attempts mixed `admin` login with `deploy` execution, which caused SSH key mismatch, path mismatch, systemd user mismatch, and runtime confusion.

## Decision
Use a single-user baseline:
- login user: `admin`
- repo path: `~/projects/oris`
- OpenClaw runtime: `~/.openclaw/`
- systemd user service: `openclaw-gateway.service`
- no cross-user execution for the baseline phase

## Additional decisions
1. OpenClaw is not installed through Python venv/pip
2. Python venv is retained only for repo-side helper tooling
3. Gateway remains loopback-only during baseline phase
4. `gateway.controlUi.allowInsecureAuth` must be disabled after onboarding
5. Remaining audit warnings are accepted temporarily because they are non-blocking in the current topology

## Consequences
- Lower operational ambiguity
- Easier troubleshooting
- Easier new-session continuity
- Safer default posture for baseline setup
