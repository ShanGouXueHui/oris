# Decision: keep ORIS on admin-based single-user baseline with reverse-proxied dashboard and Feishu websocket
Date: 2026-04-06

## Context
The server was rebuilt from scratch. Earlier failures came from cross-user runtime confusion, SSH key mismatch, and mixed auth patterns.

## Decisions
1. Keep the whole baseline under the `admin` user.
2. Keep OpenClaw gateway loopback-only on `127.0.0.1:18789`.
3. Expose the dashboard only through:
   - Nginx
   - HTTPS
   - Basic Auth
4. Keep gateway token auth enabled, but manage the token through SecretRef.
5. Keep model credentials in `~/.openclaw/secrets.json` and reference them via `keyRef` / SecretRef.
6. Use Feishu in `websocket` mode instead of webhook mode.
7. Use `pairing` for DM access control during the baseline phase.
8. Do not store any real credentials in the repository.

## Outcome
- Dashboard is reachable publicly and works through the reverse proxy.
- OpenRouter model auth works.
- Feishu bot works end-to-end and has already replied successfully in DM.

## Deferred follow-up
- Rotate Feishu App Secret because it was exposed during setup.
- Consider adding QQ Bot / Tencent-side channel using the same secrets architecture.
