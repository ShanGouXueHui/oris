# Current AI Dev Employee Task

Status: completed

Task id: `commercial-native-openclaw-ui-20260617`

Completion time: `2026-06-17T21:46:02Z`

## Final result

The native OpenClaw Gateway UI is now the primary commercial conversation interface at `https://control.orisfy.com`.

Accepted chain:

`human → native OpenClaw UI → Agent Harness tool/policy adapter → ORIS control plane → Codex executor → product/evidence back to OpenClaw`

Final browser acceptance: `PASS`.

Verified native behaviors:

- token-authenticated connection;
- new conversation;
- multiple independent conversations;
- history visibility and switching;
- refresh persistence;
- session-level deletion with the first conversation preserved;
- restricted `/admin` loading;
- restricted `/_oris-chat-shell` rollback/diagnostic route loading.

The earlier acceptance record that incorrectly marked session deletion as tested is superseded by:

`logs/dev_employee/native_openclaw_ui_acceptance/native-openclaw-ui-supplemental-acceptance-20260617T213905Z.json`

Evidence commit: `b479436a51bb1731e79fcfe98b2ec3d8b4683abd`.

## Runtime and security state

- OpenClaw Gateway remains the existing installation on `127.0.0.1:18789`;
- OpenClaw was not reinstalled or upgraded;
- Nginx root routes to native OpenClaw;
- `/admin` routes to the ORIS Web Console and remains restricted;
- `/_oris-chat-shell` remains a restricted rollback route;
- intake on `127.0.0.1:18892` is not publicly exposed;
- Gateway auth mode is token;
- Control UI device pairing is intentionally bypassed for all clients holding a valid Gateway credential through `gateway.controlUi.dangerouslyDisableDeviceAuth=true`;
- this pairing bypass is a conscious commercial-security exception and does not disable token authentication.

## Controlled product task completion

Task: `chat-oris-final-acceptance-api-20260617-051313-c802347ff17c`

Product repository: `ShanGouXueHui/oris-final-acceptance-api`

Base implementation commit: `927f1968cc86bfd5213670f4eaa171fc1a3be620`

Final product commit: `bcb93e17ea88704548101f5e4a5c460e15a80ec7`

Remote main: `bcb93e17ea88704548101f5e4a5c460e15a80ec7`

Verified:

- `GET /capabilities` implementation remains unchanged;
- existing pytest coverage passes;
- `README.md` API list now includes `GET /capabilities`;
- the completion commit changes only `README.md`;
- local HEAD and remote main match;
- product worktree is clean.

## Open item that does not block acceptance

The current `openclaw sessions --json` output did not expose usable `runtimeMs` samples for the browser conversations. Exact response latency therefore remains unmeasured. Functional acceptance is complete, but commercial rollout requires dedicated time-to-first-token and total-response latency observability.

## Next action

Do not submit or rerun the completed acceptance task.

Proceed with:

1. discovery of the stable OpenClaw tools/actions/plugin interface supported by the installed version;
2. generic ORIS action exposure through that interface, without broad prompt-keyword matching;
3. response-latency baseline and observability;
4. regression checks for native UI, authentication, Nginx routing and restricted diagnostic routes.
