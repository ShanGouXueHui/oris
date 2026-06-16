# Current AI Dev Employee Task

Status: native OpenClaw UI migration pending

Task id: `commercial-native-openclaw-ui-20260617`

Target project: `oris`

Target repository: `ShanGouXueHui/oris`

Target local path: `/home/admin/projects/oris`

## Architecture decision

The primary commercial UI will be the existing native OpenClaw Gateway UI, not the custom ORIS Web Console v5 chat shell.

Target chain:

`human → native OpenClaw UI → Agent Harness tool/policy adapter → ORIS control plane → Codex executor → evidence/status back to OpenClaw`

Responsibilities:

- OpenClaw native UI: standard conversation lifecycle, history, new conversation, switching and native prompt behavior;
- Agent Harness: backend tool contract, policy validation, structured output and fallback; not the primary UI;
- ORIS: allowlist, task identity, lifecycle, queue, lease, cancellation, retry, evidence and audit;
- Codex: implementation, tests, repair, commit and controlled push;
- custom ORIS shell: temporary restricted diagnostic/rollback route only.

OpenClaw must not be reinstalled or upgraded during this migration.

## Why the custom shell is rejected as the default UI

The page currently shown at `https://control.orisfy.com` was developed inside the ORIS repository. It is not the native OpenClaw interface. It uses OpenClaw only as an inference provider.

Observed gaps:

- no new-conversation control;
- no conversation-history sidebar;
- no session switching;
- no clear/archive lifecycle;
- one long-lived cookie silently reuses one server-side session;
- custom keyword and intent routing changes normal prompt semantics;
- task cards repeat inside the transcript;
- ordinary user prompts can be affected by ORIS-specific rules.

Do not continue rebuilding these standard capabilities in the custom shell.

## Current runtime facts

- Public entry: `https://control.orisfy.com`
- Existing native OpenClaw Gateway service: active
- Historical native OpenClaw local gateway: `127.0.0.1:18789`
- Custom ORIS Web Console service: active on `127.0.0.1:18893`
- Intake v2: active
- Bridge v3: active
- Agent Harness v1: active as backend component
- `/admin`: keep restricted for engineering diagnostics

## Completed controlled task and acceptance gap

Task:

`chat-oris-final-acceptance-api-20260617-051313-c802347ff17c`

UI status: `completed`

Product commit:

`927f1968cc86bfd5213670f4eaa171fc1a3be620`

Completed in the product commit:

- `GET /capabilities`;
- `service`, `storage` and `features` contract;
- tests for status code and response fields.

Acceptance gap:

- the requested `README.md` API-list update was not included.

Therefore this delivery is partial, not fully compliant. Repair it only after native OpenClaw UI browser acceptance.

## Migration requirements

1. Read-only discover the active native OpenClaw UI routes, session/history behavior, authentication and WebSocket contract.
2. Archive custom ORIS chat-session runtime data outside Git.
3. Prepare a reversible Nginx switch from the custom root UI to the existing OpenClaw Gateway on port 18789.
4. Preserve OpenClaw token/device pairing and WebSocket behavior.
5. Move the custom shell to a non-default rollback/diagnostic route.
6. Expose ORIS capabilities to OpenClaw as tools/actions, not through prompt keyword matching.
7. Browser-test native new conversation, history, switching and clear/archive behavior.
8. Browser-test one natural-language development goal without ORIS-specific command syntax.
9. Repair the missing README update and verify product commit SHA, remote SHA, tests and ORIS evidence.

## Next action

Do not submit another product task. First run read-only discovery of the native OpenClaw UI and effective Nginx routing. Then build a reversible migration script with backup, `nginx -t`, rollback and no OpenClaw reinstall.

Authoritative decision document:

`docs/DEV_EMPLOYEE_NATIVE_OPENCLAW_UI_DECISION_2026-06-17.md`
