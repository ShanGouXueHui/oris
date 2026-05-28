# ORIS Dev Employee Web Console Access Policy — 2026-05-29

## Purpose

This policy governs the first Web/OpenClaw product UI layer for ORIS Dev Employee.

The console is a UI façade over the already verified local intake/status service. It allows a human to submit goals, view task status, and inspect GitHub evidence without using shell commands.

## Current implementation

Script:

```text
scripts/dev_employee_web_console.py
```

Default bind:

```text
127.0.0.1:18893
```

Backend dependency:

```text
127.0.0.1:18892
```

The console:

- serves a minimal HTML UI;
- proxies `GET /api/projects` to the intake service;
- proxies `GET /api/goals` and `GET /api/goals/<task_id>` to the intake service;
- proxies `POST /api/goals` to the intake service using the local intake token;
- displays product commit SHA, product remote SHA, ORIS evidence commit SHA, and evidence files from `github_evidence`.

## Hard boundaries

The Web Console must remain local-only until an explicit access policy is implemented.

Required constraints:

1. Bind only to loopback.
2. Do not expose port `18893` directly to the public network.
3. Do not expose the intake service port directly to the public network.
4. Do not print or commit token values.
5. Do not accept arbitrary product paths from the UI.
6. Do not let the UI write queue files directly.
7. Do not let the UI invoke Codex directly.
8. Do not let the UI run shell commands.
9. Do not bypass project registry resolution.
10. Do not bypass strict autonomous result schema and skill resolver evidence validation.

## Public exposure requirements

Before exposing the console through Nginx/OpenClaw Web, implement all of the following:

- HTTPS only.
- Strong authentication, at minimum existing Basic Auth for the control plane; preferably session or SSO later.
- CSRF protection for `POST /api/goals` if accessed from a browser over a public origin.
- Request body limits.
- Audit log for submit actions.
- Rate limit for goal submission.
- Allowlist for project keys.
- Clear display that tasks may modify code and push commits.
- Emergency disable switch.

## Recommended deployment path

Phase 1: local-only smoke

- Run `scripts/dev_employee_web_console.py` manually.
- Verify `/health`, `/api/projects`, and `/api/goals/<known_task_id>`.
- Do not submit a destructive goal.

Phase 2: systemd user service

- Add a user service for the console only after local smoke passes.
- Keep loopback binding.
- Validate service health.

Phase 3: authenticated reverse proxy

- Add a restricted Nginx route only after authentication and audit requirements are implemented.
- Route public traffic to the console, not to the intake service directly.
- Keep intake service private.

## Evidence display contract

The UI should show at least:

- task status;
- product commit SHA;
- product remote SHA;
- ORIS evidence commit SHA;
- evidence commit index path;
- task run JSON;
- Codex result JSON;
- skill resolver JSON/Markdown;
- host check logs;
- Codex log.

The source of truth remains GitHub evidence, not transient local output.
