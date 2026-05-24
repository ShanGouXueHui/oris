# ORIS Dev Employee Web-to-Codex Execution Gap — 2026-05-24

## Status

Formal OpenClaw Web test failed at the intended autonomy layer.

The final acceptance API project itself passed when the host shell and Codex CLI were invoked directly, but OpenClaw Web still behaved as a planner/chat UI and emitted pseudo execution text instead of driving real host execution.

## Evidence

Observed behavior in OpenClaw Web:

- The agent acknowledged the task.
- It claimed it would use real Codex CLI, real filesystem, Git commit, and GitHub push.
- It then produced a code block resembling pseudo `exec.run(...)` instead of actually invoking the host Codex CLI.
- No real autonomous continuation happened from Web UI to Codex CLI.

This means the accepted product test validated the Codex-backed execution path only when manually triggered from host shell. It did not validate OpenClaw Web as an autonomous executor controller.

## Root cause

OpenClaw Web is currently only a task intake / chat control surface. It is not yet wired to a trusted host-side executor bridge that can:

1. receive a durable task id;
2. resolve a GitHub-backed prompt or task file;
3. invoke `/home/admin/.npm-global/bin/codex` on the ORIS host;
4. stream or persist command output under `logs/dev_employee/`;
5. commit/push evidence and state updates to GitHub;
6. return concise completion metadata to the Web UI.

The current Web agent can reason about execution but cannot reliably perform execution.

## Required product decision

Do not continue testing with more prompts alone. Prompts cannot fix a missing executor bridge.

The next implementation target must be a host-side execution bridge:

- OpenClaw Web remains the user-facing intake and approval UI.
- A local ORIS executor service performs real filesystem and Codex CLI execution.
- GitHub remains the durable memory and evidence boundary.

## MVP bridge contract

A minimum viable executor bridge should support:

### Task input

A JSON task descriptor under ORIS, for example:

```json
{
  "task_id": "formal-test-pydantic-cleanup-20260524",
  "prompt_path": "/home/admin/projects/oris/prompts/dev_employee_formal_test_pydantic_cleanup_20260524.md",
  "workdir": "/home/admin/projects",
  "codex_bin": "/home/admin/.npm-global/bin/codex",
  "extra_write_dirs": ["/home/admin/projects/oris"],
  "status": "queued"
}
```

### Executor behavior

The executor must:

1. atomically claim a queued task;
2. validate that the prompt file exists;
3. invoke Codex CLI with `exec --skip-git-repo-check` from the configured workdir;
4. write full logs to `logs/dev_employee/<task_id>.log`;
5. update `orchestration/task_runs/<task_id>.json` with status transitions;
6. never treat chat text as proof of completion;
7. require real commit SHAs and test logs before completed status.

### Web behavior

The Web UI should not pretend to execute shell commands. It should submit or reference a task descriptor and then poll/display executor status.

## Non-goals

- Do not add broad remote shell access to OpenClaw Web.
- Do not allow arbitrary unauthenticated command execution.
- Do not store secrets or private keys in task descriptors.
- Do not write product code into the ORIS repo.

## Next task

Build the MVP host executor bridge and use it to rerun the Pydantic cleanup formal test. The test is only passed when the task is initiated from OpenClaw Web/task descriptor and completed by the host executor without manual host-shell Codex invocation.
