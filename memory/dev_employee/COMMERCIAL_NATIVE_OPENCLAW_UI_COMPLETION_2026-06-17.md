# ORIS Dev Employee — Native OpenClaw Commercial UI Completion

Date: 2026-06-17

## Final result

Status: `PASS`

The public primary interface is the native OpenClaw Gateway UI. The custom ORIS Web Console is no longer the default commercial chat shell.

## Accepted architecture

`human → native OpenClaw UI → Agent Harness tool/policy adapter → ORIS task governance → Codex execution → product/test/evidence returned through OpenClaw`

## Native UI evidence

- automated Nginx and route preflight: PASS;
- token authentication: PASS;
- new and second conversation: PASS;
- history and switching: PASS;
- refresh persistence: PASS;
- session-level deletion: PASS;
- first conversation preserved after second-session deletion: PASS;
- `/admin` restricted and loads after authentication: PASS;
- `/_oris-chat-shell` restricted and loads after authentication: PASS;
- intake loopback-only: PASS;
- authoritative supplemental evidence: `logs/dev_employee/native_openclaw_ui_acceptance/native-openclaw-ui-supplemental-acceptance-20260617T213905Z.json`;
- supplemental evidence commit: `b479436a51bb1731e79fcfe98b2ec3d8b4683abd`.

## Product gap closure

- controlled task: `chat-oris-final-acceptance-api-20260617-051313-c802347ff17c`;
- product repository: `ShanGouXueHui/oris-final-acceptance-api`;
- base feature commit: `927f1968cc86bfd5213670f4eaa171fc1a3be620`;
- final documentation commit: `bcb93e17ea88704548101f5e4a5c460e15a80ec7`;
- product remote main: `bcb93e17ea88704548101f5e4a5c460e15a80ec7`;
- README API list includes `GET /capabilities`: PASS;
- py_compile: PASS;
- pytest: PASS;
- route contract: PASS;
- completion diff limited to `README.md`: PASS;
- product worktree clean: PASS;
- product SHA equals remote SHA: PASS.

## Security and operational exceptions

OpenClaw authentication remains token-based. Control UI device pairing is intentionally bypassed through `gateway.controlUi.dangerouslyDisableDeviceAuth=true` so any browser with a valid Gateway credential can connect without per-device approval. This setting is an explicit risk acceptance and must remain documented in future security reviews.

## Latency status

The browser screenshot only showed minute-level timestamps, and the installed version's session CLI returned no usable `runtimeMs` samples for these conversations. No numerical latency claim is accepted. Dedicated TTFT and total-response telemetry is the next observability requirement.

## Operational conclusion

The migration and the previously partial product task are complete. Do not rerun either acceptance task unless regression evidence shows failure.
