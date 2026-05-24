# ORIS Skill Internalization Shortlist — 2026-05-25

## Source

This shortlist is derived from the read-only intelligence report committed in ORIS:

- Commit: `cd6cc93d621cfd428016887253b32bedf0e549e6`
- Report: `logs/dev_employee/skill_audit/skill_intelligence_20260525.md`
- Policy: read-only intelligence extraction only; no third-party skill was installed or executed.

The extractor parsed 6,267 indexed items:

- reviewable read-only candidates: 1,808
- rejected for ORIS runtime: 1,088
- low-priority intelligence only: 3,371

## Decision

Do not install any third-party skill into production OpenClaw yet.

Instead, internalize safe capability patterns into ORIS-owned scripts/docs/skills after review. This avoids supply-chain and credential exposure risk while preserving useful design ideas.

## Priority capability patterns to internalize

### 1. Research/search workflow pattern

Relevant examples from the intelligence report:

- `academic-research`
- `academic-research-hub`
- `academic-deep-research`
- `academic-writing`
- `academic-writing-refiner`
- `agentic-paper-digest`
- `openclaw-free-web-search`
- `skywork-search`

ORIS internalization target:

- create a controlled `research_source_capture` workflow;
- record source URL, title, timestamp, query, summary, and confidence;
- never auto-browse authenticated pages;
- store outputs under `logs/research/` or project-specific `docs/research/`;
- require citations in final reports.

### 2. GitHub development workflow pattern

Relevant examples:

- `auto-pr-merger`
- `azure-devops`
- `bat-cat`
- `agent-commons`
- `airadar`

ORIS internalization target:

- strengthen existing GitHub-backed memory and evidence handling;
- add helpers for commit verification, changed-file summaries, and task evidence checks;
- do not auto-merge PRs or push without explicit task policy.

### 3. DevOps and execution evidence pattern

Relevant examples:

- `agentic-devops`
- `agent-self-governance`
- `agent-hq`

ORIS internalization target:

- upgrade `scripts/dev_employee_executor_bridge.py` into a supervised bridge;
- Codex performs local code/test work;
- outer bridge performs push, remote verification, and evidence commits;
- add timeout, stale-task recovery, and structured result ingestion.

### 4. Documentation/markdown/report pattern

Relevant examples:

- `clawddocs`
- `aholake-expense-tracker` as a structured markdown logging pattern
- `calorie-visualizer` as a local log-to-report pattern, not as a health feature

ORIS internalization target:

- generate concise task retrospectives automatically;
- write durable markdown and JSON logs;
- avoid chat-context bloat by committing reports to GitHub.

### 5. Coding-agent hardening pattern

Relevant examples:

- `advisory-council`
- `agent-hardening`

ORIS internalization target:

- add formal tests that detect pseudo execution;
- assert that final answers include real command output, commit SHA, remote state, and test logs;
- keep test prompts adversarial enough to expose planner-only behavior.

## Explicitly rejected runtime categories

These categories should remain blocked unless a future isolated container/sandbox policy is implemented:

- browser automation and scraping;
- anti-detection browser tooling;
- credential, password, token, or vault integrations;
- crypto, wallet, blockchain, DeFi, trading, or betting tools;
- social posting and external publishing automation;
- Gmail/calendar/email automation without account-scoped connector approval;
- installer-heavy skills with `postinstall`, shell download-exec, or broad process execution.

## Next implementation target

Build ORIS-owned supervised executor bridge v2:

1. task descriptor contains `task_id`, `prompt_path`, `product_path`, `allowed_outputs`, and `postprocess_policy`;
2. Codex writes a structured result file under `orchestration/task_runs/<task_id>.codex_result.json`;
3. outer bridge reads the result;
4. outer bridge runs final checks, Git push, GitHub remote verification, ORIS evidence update;
5. bridge marks task as completed only after remote evidence is verified.

This is the highest-value capability to internalize before installing any external skill.
