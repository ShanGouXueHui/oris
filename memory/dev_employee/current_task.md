# Current AI Dev Employee Task

Status: conversational implementation prepared; OpenClaw runtime discovery pending

Task id: `commercial-conversational-openclaw-web-20260616`

Target project: `oris`

Target repository: `ShanGouXueHui/oris`

Target local path: `/home/admin/projects/oris`

## Objective

Replace the engineering form/JSON landing page with the intended commercial interaction:

`human conversation → OpenClaw intent/session orchestration → ORIS task control plane → Codex executor → evidence/result conversation`

The accepted ORIS queue, lease, lifecycle, cancellation, retry, bridge v3, Codex, Git delivery, evidence, and audit chain remains the authority. The conversation layer is an adapter, not a competing task engine.

## Product decision

The normal user opens `https://control.orisfy.com` and sees a chat immediately.

Normal users do not manually enter:

- Console Token;
- Task ID;
- expected checks;
- commit message;
- constraints JSON;
- raw API payloads.

The existing engineering console moves to `/admin`. Raw evidence remains available only under collapsed technical details.

## Prepared implementation

- `docs/DEV_EMPLOYEE_CONVERSATIONAL_WEB_EXPERIENCE_2026-06-16.md`
- `scripts/dev_employee_chat_store.py`
- `scripts/dev_employee_openclaw_provider.py`
- `scripts/dev_employee_chat_orchestrator.py`
- `scripts/dev_employee_web_console_v3.py`
- `tests/test_dev_employee_chat_store.py`
- `tests/test_dev_employee_openclaw_provider.py`
- `tests/test_dev_employee_chat_orchestrator.py`
- `tests/test_dev_employee_web_console_v3.py`
- `scripts/dev_employee_discover_openclaw_runtime_20260616.sh`

## Conversational behavior

The user can say:

- `给 oris-final-acceptance-api 增加一个 /healthz 接口，自己完成并测试。`
- `查看进度`
- `停止任务`
- `重试`

The Web layer returns plain-language messages and a compact task card. Canonical state, Task ID, SHAs and evidence remain inside technical details.

## Provider boundary

The preferred provider is the existing OpenClaw runtime through a structured HTTP adapter.

The provider must return:

- intent;
- user-facing response;
- selected project;
- structured objective;
- derived constraints/checks;
- optional risk confirmation.

A deterministic fallback is allowed for status, cancel, retry, help, and direct single-project goal translation. It must not be represented as verified OpenClaw operation when the OpenClaw provider is unavailable.

## Current prerequisite state

- queue lifecycle P1-A server acceptance: `PASS`;
- bridge v3: `active`;
- intake v2: `active`;
- Web Console v2: `active`;
- form-based browser test: safely aborted;
- one queued test task: cancelled;
- bridge restored: `YES`;
- product SHA unchanged: `PASS`;
- product tracked worktree clean: `PASS`;
- abort evidence commit: `9def6001a6488296b9ec79a08aa74a9741d24888`.

## Current blocker

The ORIS repository does not yet contain the server's actual OpenClaw binary path, user service, listener, endpoint, or provider response contract. These must be discovered without exposing tokens, passwords, config values, or credentials.

## Next action

Run `scripts/dev_employee_discover_openclaw_runtime_20260616.sh` as Linux user `admin` on `43.106.55.255`.

The discovery is read-only, changes no service, submits no task, and commits only sanitized runtime evidence. Send only its final `===== SUMMARY =====` block. After the real OpenClaw contract is mapped, run the full conversational code tests and deploy Web Console v3. Browser acceptance will then be performed from the chat interface only.
