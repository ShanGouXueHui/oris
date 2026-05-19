# Dev Employee Planning Packet

- generated_at: `2026-05-19T20:40:06.272785+00:00`
- ok: `True`
- worker_profile: `dev_employee`
- bootstrap_ok: `True`
- latest_validation_ok: `True`
- task_summary: Dev Employee latest cycle planning packet
- objective: Provide a single repo-aware planning input for the next Dev Employee iteration.

## Worktree

- dirty: `True`
- tracked_modified_count: `12`
- untracked_count: `10`
- blocking_dirty_tracked_count: `0`
- blocking_untracked_count: `0`
- legacy_review_tracked_count: `1`
- legacy_review_untracked_count: `6`

### Blocking tracked changes

```text
<none>
```

### Blocking untracked paths

```text
<none>
```

### Legacy review paths

```text
config/insight_entity_registry.json
inputs/manual_refresh/
scripts/feishu_account_strategy_trigger.py
scripts/run_account_strategy_case_pipeline.py
scripts/run_account_strategy_trigger_loop.sh
scripts/run_insight_queue_worker_loop.sh.disabled
skills/official_source_ingest_skill/runner_providerized.py
```

## Latest validation checks

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
