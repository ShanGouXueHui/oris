# Native OpenClaw UI Decision — 2026-06-17

## Decision

The native OpenClaw Gateway UI becomes the primary end-user experience for the ORIS AI Dev Employee commercial path.

The custom ORIS Web Console v5 conversation shell must not remain the default public interface. It may be retained temporarily only as a restricted diagnostic or rollback route while migration is validated.

## Why

The custom shell was developed inside the ORIS repository. It uses OpenClaw only as a provider/inference backend and therefore does not inherit the native OpenClaw conversation lifecycle.

Observed commercial usability gaps:

- no explicit new-conversation action;
- no conversation-history sidebar;
- no clear session switching;
- no clear/archive/delete lifecycle;
- a single long-lived cookie silently reuses one server-side session;
- a custom intent router and deterministic command parser change normal prompt semantics;
- ordinary goal text can be affected by ORIS-specific routing rules;
- task cards are repeated into the transcript rather than presented as a stable side panel or status surface.

These are baseline conversation-product capabilities and should not be rebuilt in a bespoke shell while a native UI already exists.

## Target architecture

```text
human
  -> native OpenClaw UI and native conversation/session model
  -> Agent Harness tool/policy adapter
  -> ORIS control plane
  -> Codex executor
  -> ORIS evidence and task status exposed back to OpenClaw
```

Responsibilities:

- **Native OpenClaw UI**: conversation list, new conversation, switching, history, native prompt behavior and user interaction.
- **Agent Harness**: provider-neutral tool contract, policy/risk validation, structured output validation and fallback. It is not the primary user interface.
- **ORIS**: project allowlist, task identity, intake, lifecycle, queue, leases, cancellation, retry, evidence and audit.
- **Codex**: code implementation, tests, repair, commit and controlled push.
- **Custom ORIS shell**: temporary diagnostic/rollback surface only; no longer a product UX target.

## Migration constraints

1. Do not reinstall or upgrade OpenClaw during the UI switch.
2. Reuse the existing OpenClaw Gateway service and port `127.0.0.1:18789`.
3. Preserve native OpenClaw WebSocket, token and device-pairing behavior.
4. Make `https://control.orisfy.com` resolve to the native OpenClaw UI after reversible acceptance checks.
5. Keep `/admin` restricted for ORIS engineering diagnostics.
6. Move the custom ORIS shell to a non-default rollback route during migration.
7. Archive the custom shell's runtime chat sessions outside Git before removing it from the root route.
8. Do not expose Console Token, raw task JSON, secrets or provider credentials to the browser.
9. Integrate ORIS into OpenClaw as stable tools/actions, not as keyword matching inside the user prompt.
10. Require browser acceptance for new conversation, history, switching, clear/archive and one unrestricted natural-language development goal.

## Controlled task observation

The browser task `chat-oris-final-acceptance-api-20260617-051313-c802347ff17c` reached `completed` and produced product commit:

`927f1968cc86bfd5213670f4eaa171fc1a3be620`

The commit added `/capabilities` and two tests, but did not update `README.md` even though the operator explicitly requested the API list update. Therefore the task is not fully compliant and must be repaired after the native UI migration is accepted.

## Next action

Run read-only discovery against the active OpenClaw service, its native UI endpoints, session/history behavior, authentication and WebSocket route. Then prepare a reversible Nginx switch with explicit rollback and no real product submission.
