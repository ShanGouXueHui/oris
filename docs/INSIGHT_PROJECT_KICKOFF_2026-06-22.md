# Insight Project Kickoff — 2026-06-22

## Status

ORIS Dev Employee final acceptance has passed.

Accepted task:

- `demo-openclaw-web-task-board-20260622015615`
- product commit: `9ccff8fcef6eb8ef08597183eb16fb235f1f7b59`
- ORIS evidence commit: `89d54bb945013048366b53805d1ff3d027fbfe55`

## Goal

Start the formal insight product line on top of the accepted ORIS Dev Employee pipeline.

The target product should provide senior-consultant-style company and market analysis, including:

- company profile;
- market structure;
- competitor landscape;
- financial quality;
- product and capability comparison;
- strategy signals;
- risk and scenario view;
- evidence-backed executive brief.

## Historical assets found

The ORIS repo contains an existing insight track in commit history. Assets include:

- insight platform architecture and data model;
- PostgreSQL schema concepts;
- source ingest path;
- evidence and metric write path;
- company profile read path;
- report input assembly;
- citation link path;
- database helper modules under `scripts/lib/`.

Relevant current modules to audit:

- `scripts/lib/insight_db.py`
- `scripts/lib/insight_db_config.py`
- `scripts/lib/insight_db_records.py`
- `scripts/lib/insight_db_schema.py`
- `scripts/lib/insight_db_utils.py`

## Repository boundary

ORIS remains the platform and orchestration repository.

New product application code should live in a separate product repository.

Proposed project:

- project key: `oris-commercial-insight-employee`
- repo: `ShanGouXueHui/oris-commercial-insight-employee`
- local path: `/home/admin/projects/oris-commercial-insight-employee`

## Phase 0 scope

1. Audit existing insight assets in ORIS.
2. Decide reuse, rebuild, or ignore for each historical module.
3. Create a standalone product repo if it does not exist.
4. Scaffold a minimal FastAPI service.
5. Add request and response models for insight tasks.
6. Add one stub workflow for company profile or executive brief.
7. Add pytest coverage.
8. Register the product repo in ORIS project registry.
9. Record product commit SHA and ORIS evidence.

## Phase 0 acceptance

- Product code is outside ORIS.
- ORIS registry has the new project key.
- Tests pass.
- First endpoint returns structured evidence-aware output.
- Migration report exists.
- ORIS evidence records the product commit SHA.
