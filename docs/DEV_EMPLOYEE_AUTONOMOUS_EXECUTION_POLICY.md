# AI Dev Employee Autonomous Execution Policy

## Purpose

This policy records the commercial execution rules validated during the 2026-05-23 ORIS/OpenClaw/Codex bring-up session.

ORIS is the AI employee platform. OpenClaw Web is the control entrypoint. Codex CLI is the real coding executor. GitHub is the durable delivery and memory boundary.

## Architecture

Validated architecture:

- OpenClaw Web: user-facing task intake and control UI.
- ORIS Free Mesh: model routing layer for general reasoning and chat.
- Codex CLI: real coding executor on the host filesystem.
- GitHub: repository, commit, registry, and handoff memory.
- ORIS repository: platform orchestration, routing policy, project registry, governance, diagnostics, and logs.
- Business projects: independent repositories under `/home/admin/projects/<repo>`.

## Non-negotiable execution rule

Development tasks must not be satisfied by simulated tool output. The agent must verify work against:

- real filesystem paths;
- exact command output;
- test output;
- Git commit SHA;
- GitHub remote state;
- ORIS registry state when applicable.

For coding tasks, use Codex CLI as the execution backend. Do not output pseudo tool calls as if they were real actions.

## Codex execution rule

Existing project tasks should run Codex inside the target project path. New project tasks should start from `/home/admin/projects` and include `exec --skip-git-repo-check` after the `exec` subcommand.

The tested successful pattern for a new project is:

- work root: `/home/admin/projects`
- writable additional directory: `/home/admin/projects/oris`
- sandbox: `workspace-write`
- subcommand: `exec --skip-git-repo-check`

## Durable task memory

Chat history is not sufficient for commercial execution. Long-running tasks must persist state before and during work.

Required durable files:

- `memory/dev_employee/current_task.json`
- `memory/dev_employee/current_task.md`
- `orchestration/task_runs/<task_id>.json`
- `logs/dev_employee/latest_task_progress.json`
- `logs/dev_employee/latest_task_progress.md`

Each state record should include task id, status, target project, target repo, target path, current step, completed steps, failed steps, next action, last error, last commit SHA, test result, blocked reason, and update time.

## Autonomous behavior

The AI dev employee should continue execution when the next step is safe and within policy. It should not stop at planning when it can proceed.

Expected behavior:

- Missing project dependency inside a project virtual environment: install from project requirements and rerun tests.
- Test failure: inspect traceback, patch code, rerun tests.
- Missing Git remote: add the expected remote and retry push.
- Missing GitHub repository: create it if the task explicitly allows repository creation.
- Registry update needed: patch only `orchestration/project_registry.json`, preserving existing structure.
- Runtime dirty files in ORIS: do not commit them unless explicitly requested.

## Stop conditions

The agent should stop and request user action only for policy boundaries, such as production authorization, account login, infrastructure service changes, destructive operations, or actions outside the approved install scope.

## Forbidden behavior

The AI dev employee must not:

- return only a plan when execution is possible;
- print pseudo tool calls as if they were real actions;
- claim command success without exact output;
- claim remote push success without verifying remote state;
- return only a branch name as a commit reference;
- write new business code into the ORIS platform repository;
- overwrite the `project_registry.json` structure;
- commit environment files, credential material, virtual environments, caches, or runtime-generated noise.

## Completion requirements

A completed development task must return task id, repository URL, local path, product commit SHA, ORIS registry commit SHA if updated, changed files, exact static check output, exact test output, exact push result, known dirty files intentionally left uncommitted, and confirmation that no product code was written inside ORIS.

## Validated status as of 2026-05-23

Validated:

- OpenClaw Web can connect to ORIS Free Mesh through native `oris/free-auto` provider.
- Gateway token-only access is usable after removing conflicting external UI authentication blockers.
- Codex CLI 0.133.0 is installed and authenticated through ChatGPT.
- Codex CLI can create real files on the host filesystem.
- GitHub CLI is logged in and configured for SSH Git operations.
- `oris-dev-smoke-app` was created as an independent GitHub repository.
- ORIS `project_registry.json` was updated with `oris-dev-smoke-app`.

Pending:

- Full OpenClaw Web-to-Codex autonomous task execution with durable task memory.
- Final acceptance project `oris-final-acceptance-api`.
