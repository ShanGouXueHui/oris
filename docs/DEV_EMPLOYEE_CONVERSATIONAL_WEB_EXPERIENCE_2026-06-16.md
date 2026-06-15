# ORIS Dev Employee Conversational Web Experience — 2026-06-16

## Product correction

The current form-and-JSON Web Console is an engineering/admin control plane. It is not the intended commercial user experience.

The commercial entry at `https://control.orisfy.com` must be conversation-first:

`human conversation → OpenClaw intent/session orchestration → ORIS task control plane → Codex executor → evidence/result conversation`

The user should not need to understand Task IDs, raw JSON, queue suffixes, Git SHAs, Console Tokens, or retry APIs in normal use.

## User experience principles

1. The primary screen is a chat, not a form.
2. The human states a goal and constraints in natural language.
3. ORIS/OpenClaw decides routine engineering details autonomously.
4. Normal low-risk tasks begin without asking the human to choose implementation details.
5. Confirmation is required only for policy boundaries such as destructive actions, production changes, billing, secrets, compliance, or irreversible external effects.
6. Progress appears as concise conversational updates and a compact task card.
7. Raw technical evidence is hidden under an expandable `Technical details` section.
8. Cancel and Retry are plain-language actions on the task card and are also understood as chat commands.
9. The admin console is moved to a separate restricted route such as `/admin`.
10. The system must preserve all existing queue, lease, cancellation, retry, evidence, and audit semantics behind the chat adapter.

## Target conversation

Example:

**Human**

> 给 oris-final-acceptance-api 增加一个 `/healthz` 接口，自己完成并测试。

**ORIS / OpenClaw**

> 已理解。我会在独立产品仓库中完成接口、测试、提交和证据记录，不修改 ORIS 平台代码。任务已开始。

Task card:

- Project: ORIS Final Acceptance API
- Status: Planning / Developing / Testing / Delivering / Completed
- Safe actions: Stop task
- Advanced: Technical details

During execution:

> 代码已完成，正在运行完整测试。

On completion:

> 已完成。全部测试通过，代码已提交并推送。可以查看变更摘要或技术证据。

## Architecture roles

### OpenClaw conversational layer

Owns:

- conversation/session state;
- natural-language intent extraction;
- project identification;
- missing-information detection;
- risk/policy confirmation;
- user-facing responses;
- conversation-to-task translation;
- task progress narration.

Does not own:

- direct product file mutation;
- direct queue-file mutation;
- Git delivery;
- Codex process ownership.

### ORIS control plane

Owns:

- structured task creation;
- idempotency;
- lifecycle state;
- queue/lease/heartbeat;
- cancellation/retry;
- project policy and allowlist;
- evidence and audit.

### Codex executor

Owns:

- implementation;
- local testing and repair;
- structured execution result;
- product commit/push through ORIS-controlled delivery policy.

## Main Web routes

- `/` — conversational AI Dev Employee experience.
- `/api/chat/sessions` — create/list chat sessions.
- `/api/chat/sessions/{session_id}/messages` — submit/read messages.
- `/api/chat/sessions/{session_id}/stream` — progress event stream.
- `/api/chat/tasks/{task_id}/cancel` — conversational cancel action.
- `/api/chat/tasks/{task_id}/retry` — conversational retry action.
- `/admin` — restricted engineering/admin console.

The public chat API is an adapter. It must call the existing intake/control APIs rather than duplicate lifecycle rules.

## Conversation state

Each session stores:

- `session_id`;
- authenticated user/tenant identity;
- selected or inferred project;
- conversation messages;
- current task id;
- task lineage;
- pending policy confirmation;
- summarized context;
- created/updated timestamps.

Messages use typed roles:

- `user`;
- `assistant`;
- `system_event`;
- `task_card`;
- `confirmation_request`.

## Task creation policy

A natural-language message becomes a task only when:

- a supported project is identified;
- the objective is sufficiently concrete;
- no policy confirmation is pending;
- idempotency prevents duplicate submission.

For ordinary engineering tasks, OpenClaw should autonomously derive:

- task id;
- implementation constraints;
- relevant checks;
- commit message;
- execution timeout;
- evidence requirements.

These derived fields remain visible only under technical details.

## Plain-language lifecycle mapping

- `accepted`, `validated`, `queued` → `Preparing`
- `claimed`, `planning` → `Planning`
- `executing` → `Developing`
- `local_checks_passed` → `Testing complete`
- `committing`, `pushing` → `Delivering`
- `completed` → `Completed`
- `cancelling` → `Stopping safely`
- `cancelled` → `Stopped`
- failure states → `Needs attention`

The detailed canonical state remains available to administrators and evidence consumers.

## Interaction design

The main page contains:

- conversation history;
- one multiline message input;
- send button;
- optional attachment button later;
- a small project indicator when inferred;
- compact task card embedded in the conversation;
- suggested user actions such as `查看进度`, `停止任务`, `重试`, `查看结果`.

Normal users do not see:

- Console API Token input;
- raw project selector unless project inference is ambiguous;
- raw Task ID field;
- constraints/checks/commit-message fields;
- raw JSON response panels.

## Admin console

The existing form/JSON console remains useful for engineering diagnostics, but must move behind `/admin` and be clearly labeled:

`ORIS Admin Console — engineering diagnostics`

It is not the default landing page and is not used for normal product acceptance.

## Migration sequence

1. Safely abort the current form-based browser test and restore bridge v3.
2. Preserve P1-A queue/lifecycle services unchanged.
3. Move the current form console to `/admin`.
4. Add a persistent chat-session store and chat adapter.
5. Add conversation-first HTML/UI at `/`.
6. Connect chat task cards to existing status/cancel/retry APIs.
7. Add OpenClaw intent orchestration behind an explicit provider interface.
8. Add deterministic fallback for status/cancel/retry commands when the model is unavailable.
9. Run server-side tests without a product task.
10. Ask the operator to log in and test only the conversational flow.

## Acceptance criteria

The commercial Web experience is accepted when the operator can:

1. log in to `https://control.orisfy.com`;
2. see a chat interface immediately;
3. type one natural-language development goal;
4. receive a plain-language understanding/plan response;
5. see a compact task card and progress without reading JSON;
6. stop or retry using normal language or one visible action;
7. expand technical evidence only when needed;
8. never manually enter a Task ID, commit message, expected checks, or Console Token in the normal flow.

## Current decision

The form-based browser acceptance is rejected as a product UX test. It remains an admin diagnostic capability only. The next implementation task is the conversational OpenClaw Web adapter and UI, while preserving the already-accepted ORIS queue and Codex execution chain.
