# ORIS Dev Employee Failure Evidence Plan — 2026-05-26

## Purpose

Close the remaining evidence gap in the supervised bridge.

Successful tasks already produce GitHub-verifiable evidence:

- product commit SHA;
- product remote SHA;
- host-side check logs;
- ORIS task run JSON;
- skill resolver reports for strict autonomous tasks.

The remaining gap is failure observability. When a task fails before the success path, for example:

- `blocked_result_schema_invalid`;
- `blocked_skill_resolution_invalid`;
- `blocked_codex_result_not_passed`;
- `blocked_host_checks_failed`;
- `blocked_product_push_failed`;
- `blocked_oris_push_failed`;
- `codex_failed`;
- `bridge_exception`,

the bridge must persist and push enough ORIS evidence for the next autonomous cycle to inspect the failure from GitHub without asking the human to paste local logs.

## Required behavior

On every failure path, the bridge should write and attempt to commit/push:

- `orchestration/task_runs/<task_id>.json`;
- `orchestration/task_runs/<task_id>.failure_result.json`;
- `logs/dev_employee/latest_task_progress.json`;
- `logs/dev_employee/latest_task_progress.md`;
- any available skill resolver report under `logs/dev_employee/skill_resolution/`;
- any available host check logs for this task.

Queue runtime files remain ignored and must not be committed.

## Evidence contract

Failure evidence JSON should include:

- `task_id`;
- failure `status`;
- `updated_at`;
- `strict_result_schema`;
- `task_objective`;
- `failure_stage` / `status`;
- `failure_details`;
- `codex_result_path` if available;
- `codex_log_path` if available;
- `skill_resolver_report_json` if available;
- `skill_resolver_report_markdown` if available;
- `checks` if host checks ran;
- `product_result` / `oris_result` if those stages ran;
- `next_recommended_action`.

## Policy boundaries

- Do not commit `.env`, credentials, private keys, browser profiles, `.venv`, caches, or queue runtime JSON.
- Do not commit product code into the ORIS repository.
- Failure evidence is diagnostic metadata only; it must not include secrets.
- If GitHub push itself fails, write local evidence and mark `oris_evidence_push_failed` in the local task state.

## Next implementation target

Update `scripts/dev_employee_supervised_bridge_v2.py` so `fail_task()` calls a reusable failure evidence commit helper before moving the queue descriptor to `.failed.json`.

