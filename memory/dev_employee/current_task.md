# Current AI Dev Employee Task

Status: server acceptance passed; browser acceptance pending

Task id: `commercial-conversational-agent-harness-web-20260617`

Target project: `oris`

Target repository: `ShanGouXueHui/oris`

Target local path: `/home/admin/projects/oris`

## Current architecture

The deployed commercial interaction chain is:

`human → Agent Harness → OpenClaw provider → ORIS control plane → Codex executor → evidence/result conversation`

Responsibilities remain separated:

- Agent Harness: deterministic control commands, provider routing/fallback, structured-output validation, allowlist/risk policy, sanitized trace metadata;
- OpenClaw: model-backed intent extraction and response drafting through the existing Gateway installation;
- ORIS: task identity, lifecycle, queue, lease, cancellation, retry, policy, evidence and audit;
- Codex: implementation, testing, repair, commit and controlled push.

OpenClaw was not reinstalled or upgraded.

## Deployed Web experience

- Public entry: `https://control.orisfy.com`
- `/`: conversation-first `ORIS AI 开发员工`
- `/admin`: restricted engineering diagnostics console
- Web runtime: v5
- Agent Harness: v1

The normal user does not enter Console Token, Task ID, expected checks, commit message, constraints JSON, or raw API payloads.

## Completed server acceptance

- OpenClaw Gateway: `active`
- Agent Harness provider probe: `PASS`
- Web conversation page contract: `PASS`
- `/admin` contract: `PASS`
- Chat API smoke: `PASS`
- Harness trace: `PASS`
- bridge: `active`
- intake: `active`
- Web Console: `active`
- product SHA unchanged: `PASS`
- product worktree clean: `PASS`
- real product task submitted: `NO`
- real product change: `NO`

## Runtime/Git boundary

Live routing state, runtime plans, runtime state, execution logs and latency telemetry are no longer tracked by Git. Raw chat sessions and raw Harness traces are ignored and must not enter GitHub.

The historical stash was privately archived with checksums and safely dropped after all validation passed.

Latest finalization evidence commit:

`db38c220c41709da959c9e7add13888216d99ccb`

Final private archive manifest:

`5a6872aff7280634576a3a97329c40485cec99d25453fd27b70246cb553ebf15`

## Current browser test

The first browser test is intentionally a no-task smoke.

1. Open `https://control.orisfy.com` and complete Basic Auth.
2. Confirm the landing page is a chat titled `ORIS AI 开发员工`.
3. Confirm no engineering form fields are visible.
4. Send `帮助`.
5. Confirm the response explains how to describe a development goal, without creating a task.
6. Send `查看进度`.
7. Confirm the response states that the current session has no task.

Do not submit a real engineering goal during this first smoke. After the safe browser experience is accepted, the next stage will run one controlled conversational product task and verify task card, progress narration, Codex delivery and evidence presentation.

## Next action

The operator logs in through the public Web entry and reports the observed page and responses, preferably with a screenshot. No server command is required for this step.
