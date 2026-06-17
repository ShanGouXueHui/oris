# ORIS Dev Employee — Current State After Native OpenClaw Completion

Date: 2026-06-17

This file supersedes pending-migration statements in earlier 2026-06-17 state and handoff documents.

## Current production-facing state

- public root: native OpenClaw Gateway UI;
- Gateway: existing service on `127.0.0.1:18789`;
- ORIS Web Console: restricted at `/admin`, upstream `127.0.0.1:18893`;
- custom ORIS chat shell: restricted rollback/diagnostic route `/_oris-chat-shell`;
- intake: loopback-only on `127.0.0.1:18892`;
- Nginx duplicate server blocks: removed;
- OpenClaw auth: token;
- Control UI device pairing: bypassed for clients with valid token;
- active product task: none.

## Completed task

`commercial-native-openclaw-ui-20260617` is complete.

The controlled product task `chat-oris-final-acceptance-api-20260617-051313-c802347ff17c` is also fully complete after the README repair.

Final product SHA: `bcb93e17ea88704548101f5e4a5c460e15a80ec7`.

## Next commercial priority

1. discover the stable tools/actions/plugin contract in the installed OpenClaw version;
2. expose generic ORIS actions through that contract;
3. eliminate broad keyword-based task creation from the primary path;
4. establish TTFT and total-response latency telemetry;
5. preserve rollback, authentication, audit and evidence guarantees.
