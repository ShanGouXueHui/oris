# ORIS Dev Employee Bridge Formal Test Observation — 2026-05-25

## Observation

A formal bridge test was run through `scripts/dev_employee_executor_bridge.py --once` with queued task:

- `formal-test-pydantic-cleanup-20260524`

The bridge successfully claimed the queued task and invoked Codex CLI on the host.

Evidence from the runtime log shows:

- host bridge process was running: `python3 scripts/dev_employee_executor_bridge.py --once`;
- Codex CLI process was running under `/home/admin/.npm-global/.../codex.js exec`;
- Codex sandbox process was executing commands in `/home/admin/projects/oris-final-acceptance-api`;
- the formal prompt was passed into Codex CLI;
- the sandbox had `network: restricted`;
- the product code diff was generated, including Pydantic v2 cleanup:
  - `ConfigDict(extra="forbid")`;
  - `.model_dump()` replacing `.dict()`;
  - endpoint handlers were changed to async functions;
- pytest command was invoked with `PYTHONPATH=/home/admin/projects/oris-final-acceptance-api`;
- Codex later reported a blocker around Git evidence: local commit existed, but push / `ls-remote` verification failed.

## Interpretation

The host-side bridge MVP successfully proves:

```text
queued task descriptor -> bridge claim -> Codex CLI process -> real sandbox command execution -> log output
```

However, it does not yet fully solve the completion path because Codex still attempts GitHub push / remote verification inside a network-restricted sandbox.

This is consistent with the previous final-acceptance lesson: Codex can perform code generation and local checks, but GitHub repo creation, push, and remote verification should be handled by the outer host bridge when the Codex sandbox has restricted network.

## Required next bridge improvement

Upgrade the bridge from a pure Codex invoker to a supervised executor with post-processing:

1. Codex performs local code/test work.
2. Codex writes a structured result file under ORIS, for example:
   - `orchestration/task_runs/<task_id>.codex_result.json`
3. The outer bridge reads the result file.
4. The outer bridge performs Git push and GitHub remote verification from the host shell, outside Codex sandbox.
5. The outer bridge commits ORIS evidence/logs and updates task status to completed or blocked.

## Logging policy

Future runs should avoid pasting long terminal logs into chat. Logs should be committed to GitHub under:

- `logs/dev_employee/`
- `orchestration/task_runs/`

The chat should only receive commit SHA and concise status.
