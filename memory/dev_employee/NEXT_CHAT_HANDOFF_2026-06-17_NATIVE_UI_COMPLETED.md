# Next Chat Handoff — Native OpenClaw UI Completed

Date: 2026-06-17

Read this file before the older `NEXT_CHAT_HANDOFF_2026-06-17.md` when continuing the project.

## Completed

- native OpenClaw is the primary public UI;
- browser acceptance including session-level deletion passed;
- token authentication remains enabled;
- device pairing is intentionally bypassed for authenticated Control UI clients;
- `/admin` and `/_oris-chat-shell` remain restricted;
- intake remains loopback-only;
- product README gap for `GET /capabilities` is repaired;
- product tests, commit, push and remote SHA are verified;
- current commercial migration task is closed.

## Do not do

- do not reinstall or upgrade OpenClaw as part of continuation;
- do not restore the custom shell as the default UI;
- do not submit another acceptance task;
- do not use broad prompt keyword matching as the primary task-creation mechanism;
- do not claim a latency number until dedicated telemetry exists.

## Continue with

Read-only discovery first, then implement the smallest stable OpenClaw tool/action/plugin adapter that exposes ORIS task governance while keeping Codex as executor. In parallel, add response-latency observability with TTFT and total completion duration.
