# ORIS Autonomous Dev Employee Runtime v2 Acceptance

Date: 2026-06-22
GitHub issue: https://github.com/ShanGouXueHui/oris/issues/15
Status: acceptance project created

## Decision

ORIS must be upgraded from an interactive OpenClaw/tool-execution flow into a persistent autonomous AI development employee runtime.

OpenClaw Web is the control plane only. It is used to submit goals, inspect progress, and approve bounded high-risk actions. It must not be the long-running execution runtime.

The runtime must continue working even if the browser, SSH terminal, OpenClaw chat, or prior model context disconnects.

## Target Capability

After a human submits a high-level project goal, ORIS must autonomously:

1. Decompose the goal into modules.
2. Generate compact module context packs.
3. Use Codex CLI and validated skills to implement modules.
4. Run compile, unit, strict-warning, and module-specific tests.
5. Repair ordinary failures without asking humans.
6. Commit and push code plus evidence to GitHub.
7. Continue to the next module only after tests and GitHub evidence pass.
8. Run deployment smoke tests at deployable checkpoints.
9. Produce final execution, testing, deployment, and acceptance reports.

## Required Runtime Components

1. Persistent autonomous task queue.
2. Detached background worker service.
3. Agent-loop state machine.
4. Context manager.
5. Short-term and long-term memory manager.
6. Skill resolver with quarantine and validation.
7. Codex CLI execution adapter.
8. Module planner.
9. Test runner.
10. Failure classifier and self-repair loop.
11. GitHub evidence writer.
12. Deployment smoke verifier.
13. Progress/status API.
14. Web-readable execution dashboard state.

## Agent Loop

Each module must run through a bounded loop:

```text
observe -> plan -> act -> test -> reflect -> repair -> report -> commit -> push -> verify -> continue_or_block
```

Required properties:

- persistent state;
- resumability after worker restart;
- heartbeat;
- max attempts per module;
- max repair attempts per failure;
- terminal and non-terminal status classification;
- failure code classification;
- human escalation only for approved boundaries.

## Context Management

Do not rely on OpenClaw chat history as durable memory.

Before every Codex execution, generate a compact context pack containing:

- project objective;
- current module objective;
- acceptance criteria;
- relevant files;
- latest test failures;
- previous module summary;
- active constraints;
- current repository status.

Durable memory must be written to GitHub and ORIS evidence files.

## Module Evidence Rule

Every module must create and commit:

- `docs/testing/MODULE_<N>_TEST_PLAN.md`
- `reports/testing/module_<N>_test_result.json`
- `reports/testing/latest_test_result.json`
- `reports/execution/module_<N>_execution_report.md`

A module is not complete until:

1. implementation is committed and pushed;
2. test plan is committed and pushed;
3. test result JSON is committed and pushed;
4. execution report is committed and pushed;
5. result commit SHA is recorded in ORIS evidence.

## Skill Resolver Rule

If a required skill is missing, ORIS must autonomously:

1. discover candidate skill;
2. download into quarantine;
3. validate manifest/source;
4. run smoke test;
5. record `skill_resolution.json`;
6. use the skill only after validation.

Unvalidated downloaded code must not be executed.

## Deployment Verification Rule

For deployable products, ORIS must create:

- `reports/deployment/staging_smoke_result.json`
- `reports/deployment/production_smoke_result.json` when production deployment is explicitly authorized
- `reports/deployment/commercial_deployment_report.md`
- `reports/acceptance/final_acceptance_report.md`

Deployment must not be marked successful unless smoke tests prove endpoint/service health.

## Human Escalation Boundary

ORIS may block only for:

- missing credentials;
- unsafe production operation;
- destructive database operation;
- paid resource creation;
- legal/compliance/security risk;
- repeated unrecoverable failure after bounded repair attempts.

Routine engineering decisions must be handled autonomously.

## Acceptance Modules

### Module A: Architecture and State Machine Design

Deliver architecture doc, state machine schema, failure taxonomy, acceptance criteria, and tests for status transitions.

### Module B: Persistent Queue and Run State Schema

Deliver queue schema, run schema, module state schema, persistent backend, and tests for resume/recovery.

### Module C: Detached Worker Service

Deliver worker loop, heartbeat, resumable processing, service definition/runbook, and tests for restart safety.

### Module D: Context Pack Generator

Deliver context pack format, relevant-file selection, failure-context summary, previous-module summary, and deterministic tests.

### Module E: GitHub Evidence Writer

Deliver evidence writer for module plans/results/reports, latest pointer files, commit SHA index, and evidence schema tests.

### Module F: Module Planner and Bounded Agent Loop

Deliver module planner, bounded loop executor, test/repair policy, next-module gate, and tests that prevent next-module execution until evidence passes.

### Module G: Skill Resolver Integration

Deliver quarantine directory, manifest validation, smoke test runner, skill resolution evidence, and tests blocking unvalidated skills.

### Module H: Deployment Smoke Verifier

Deliver staging/production smoke result schemas, endpoint verifier, rollback recommendation, and smoke-result validation tests.

### Module I: End-to-End Demo Using Insight Product

Use `ShanGouXueHui/oris-commercial-insight-employee` as the demo product. ORIS must rebuild or replace the insight capability through Runtime v2, push implementation and evidence to GitHub, run final acceptance, and produce a final report.

## Operational Recommendation

Stop expanding the current interactive Insight Product run after Module 1 is safely committed. Treat it as evidence that the current interactive model is insufficient.

Then prioritize this Runtime v2 acceptance project. After Runtime v2 exists, use it to rebuild the insight capability cleanly from first principles, referencing or deleting legacy insight code as appropriate.

## Final Acceptance Criteria

The project is accepted only when a verifier can inspect GitHub and confirm:

1. Runtime v2 modules A-I are completed.
2. Every module has a test plan, result JSON, execution report, and commit SHA.
3. Worker execution is detached from browser/terminal.
4. Context pack generation works.
5. Skill resolver records validation evidence.
6. Module advancement is blocked unless tests and evidence pass.
7. Insight product rebuild is executed by the upgraded ORIS runtime.
8. Deployment smoke and final acceptance reports exist.
9. No manual routine engineering decisions were required during the final demo.
