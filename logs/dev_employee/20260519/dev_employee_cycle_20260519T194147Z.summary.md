# Dev Employee Cycle Summary

- timestamp_utc: 20260519T194147Z
- branch: main
- repo_dir: /home/admin/projects/oris
- task_code: dev_employee_cycle
- self_heal_log_drift: 1

## Preflight status before self-heal

```text
 M config/insight_entity_registry.json
 M orchestration/active_routing.json
 M orchestration/execution_log.jsonl
 M orchestration/feishu_event_dedupe.json
 M orchestration/free_eligibility.json
 M orchestration/runtime_plan.json
 M orchestration/runtime_state.json
?? inputs/manual_refresh/
?? logs/dev_employee/latest_execution_approval.json
?? logs/dev_employee/latest_execution_approval.md
?? scripts/feishu_account_strategy_trigger.py
?? scripts/run_account_strategy_case_pipeline.py
?? scripts/run_account_strategy_trigger_loop.sh
?? scripts/run_insight_queue_worker_loop.sh.disabled
?? skills/official_source_ingest_skill/runner_providerized.py
```

## Self-healed tracked dev_employee logs

```text
```

## Git pull
- git_checkout_rc: 0
- git_pull_rc: 0
- compile_rc: 0
- smoke_rc: 0
- smoke_json: {"codex_dry_run": true, "executor_plan": ["codex_executor", "validation_pipeline"], "ledger_path": "run/dev_employee/task_runs.jsonl", "ledger_written": true, "model_role": "coding_planning", "ok": true, "task_run_id": "dev-00255b32b84c", "worker_profile": "dev_employee"}
- validation_rc: 0
- validation_json: {"check_count": 12, "markdown_path": "run/dev_employee/cycle_validation_report.md", "ok": true, "report_path": "run/dev_employee/cycle_validation_report.json"}

## Validation report

- ok: true
- check_count: 12

| Check | Return code | Result |
| --- | ---: | --- |
| `python_compile_oris_vnext` | 0 | pass |
| `dev_employee_bootstrap_reader` | 0 | pass |
| `dev_employee_smoke_no_ledger` | 0 | pass |
| `codex_executor_gate_smoke` | 0 | pass |
| `ledger_event_smoke` | 0 | pass |
| `log_summarizer_smoke` | 0 | pass |
| `planning_packet_smoke` | 0 | pass |
| `execution_packet_smoke` | 0 | pass |
| `execution_approval_smoke` | 0 | pass |
| `execution_approval_exporter` | 0 | pass |
| `commercial_readiness_smoke` | 0 | pass |
| `commercial_readiness_exporter` | 0 | pass |

## Key result

```json
{"ok":true,"timestamp_utc":"20260519T194147Z","compile_rc":0,"smoke_rc":0,"validation_rc":0,"summary_file":"logs/dev_employee/20260519/dev_employee_cycle_20260519T194147Z.summary.md","validation_file":"logs/dev_employee/20260519/dev_employee_cycle_20260519T194147Z.validation.txt"}
```

## Git status captured before log commit

```text
 M config/insight_entity_registry.json
 M logs/dev_employee/latest_commercial_readiness.json
 M logs/dev_employee/latest_commercial_readiness.md
 M orchestration/active_routing.json
 M orchestration/execution_log.jsonl
 M orchestration/feishu_event_dedupe.json
 M orchestration/free_eligibility.json
 M orchestration/runtime_plan.json
 M orchestration/runtime_state.json
?? inputs/manual_refresh/
?? logs/dev_employee/20260519/dev_employee_cycle_20260519T194147Z.summary.md
?? logs/dev_employee/20260519/dev_employee_cycle_20260519T194147Z.validation.txt
?? logs/dev_employee/latest_execution_approval.json
?? logs/dev_employee/latest_execution_approval.md
?? scripts/feishu_account_strategy_trigger.py
?? scripts/run_account_strategy_case_pipeline.py
?? scripts/run_account_strategy_trigger_loop.sh
?? scripts/run_insight_queue_worker_loop.sh.disabled
?? skills/official_source_ingest_skill/runner_providerized.py
```
