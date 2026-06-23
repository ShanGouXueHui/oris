# Current State: Post Runtime v2 and Insight Rebuild Stage 1

Date: 2026-06-23

## Summary

This chat completed ORIS Autonomous Dev Employee Runtime v2 final acceptance and started the commercial insight employee rebuild using the accepted Runtime v2 substrate.

The conversation is long enough that the next work should start in a new chat using the handoff prompt stored in GitHub. Do not rely on chat memory alone.

## Runtime v2 Acceptance Result

Repository: `ShanGouXueHui/oris`

Runtime v2 final acceptance is complete.

Accepted modules:

- Module A: Architecture and State Machine Design
- Module B: Persistent Run Store and Queue Contract
- Module C: Autonomous Worker Loop and Repair Policy
- Module D: Tool Executor Adapter and Evidence Contract
- Module E: GitHub Evidence Publisher and Run Evidence Index
- Module F: Approval Gate and Control Plane Contract
- Module G: End-to-End Runtime Harness and Acceptance Runner
- Module H: Final Acceptance Gate and Insight Rebuild Handoff

Final acceptance report:

- `docs/runtime_v2/RUNTIME_V2_FINAL_ACCEPTANCE_REPORT.md`
- Runtime v2 final ORIS reference after script fix: `896bdc67942a27cea98b8a4eb8f49d946795a741`

Known correction already made:

- Module H final report originally had a heredoc/backtick issue that caused the product repo name to be interpreted by shell.
- The final report and official Module H script were fixed in GitHub.
- Only one official Module H script remains: `scripts/bootstrap_runtime_v2_module_h.sh`.

## Product Rebuild Result

Repository: `ShanGouXueHui/oris-commercial-insight-employee`

The first stage of Runtime v2 backed product rebuild is complete.

Accepted rebuild modules:

1. Module 1: Architecture Alignment with Runtime v2
2. Module 2: Domain Contracts
3. Module 3: Evidence Ingestion
4. Module 4: Brief Generation Pipeline
5. Module 5: Quality Gates and Limitations
6. Module 6: API Surface and Acceptance

Product final reference after Module 6:

- `8a66d3858c42721fa44f6bae3c4a66b7140f569b`

Module 6 evidence:

- `reports/testing/latest_test_result.json`
- `reports/execution/insight_rebuild_module_6_execution_report.md`
- status: `passed`
- test exit code: `0`
- `first_stage_rebuild_closed=true`

## Product Current API Surface

FastAPI version is now `0.2.0`.

Available endpoints:

- `GET /healthz`
- `GET /healthz/details`
- `POST /insights/executive-brief` legacy-compatible deterministic endpoint
- `GET /insights/rebuild/acceptance`
- `POST /insights/rebuild/brief`

## Environment and Systems

- ORIS repo local path: `/home/admin/projects/oris`
- Product repo local path: `/home/admin/projects/oris-commercial-insight-employee`
- Current execution host uses `admin` user under `/home/admin/projects`.
- Development environment historically includes Singapore server `43.106.55.255`, user `cpsdev`.
- Production environment historically includes Hangzhou server `8.136.28.6`, user `deploy`; do not touch without explicit authorization.
- No production database is configured for this product yet.
- No cache is configured yet.
- No external model/provider is integrated in the product yet.
- Evidence is GitHub-backed via reports and execution logs.

## Interaction and Process Rules

- Continue automatically for GitHub-side updates.
- Ask the user to execute commands only when local authenticated server execution is required.
- Provide one short copy-paste command block for required local execution.
- Do not ask the user to paste long logs.
- Read evidence from GitHub after scripts push reports.
- Keep terminal output short.

## Engineering Rules

- One official executable entry point per module/workflow.
- No `_v2.sh`, `_v3.sh`, `compat.sh`, or duplicated official bootstrap scripts.
- Git history is backup; avoid backup scripts in repo.
- Do not use `set -e` in user-facing scripts or commands.
- Keep product design layered and decoupled.
- Separate config from logic.
- Build a generic commercial version, not a one-off company-specific implementation.

## Immediate Next Task

Start Insight Rebuild Module 7: Runtime v2 Orchestration and Real Evidence Source Integration.

Recommended scope:

- product-side Runtime v2 orchestration adapter contract;
- source connector abstraction;
- config-separated source/model/runtime settings;
- deterministic local source connector for tests;
- boundary for future real web/search/model providers;
- evidence persistence plan;
- API/runtime integration report;
- tests and GitHub evidence.

Do not jump directly to deployment or production monetization before Module 7 establishes orchestration and real evidence-source boundaries.
