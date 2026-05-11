# Runtime Simplification Policy

Date: 2026-05-11
Status: accepted

## Core policy

ORIS uses a simplified single-runtime evolution model.

Guidelines:
- Maintain one primary runtime path.
- Prefer direct replacement over long-term coexistence.
- Keep architecture understandable and compact.
- Reduce duplicated orchestration and routing logic.
- Use Git history and external backups for rollback.

## Migration guidance

During refactors:
1. Create external backup if needed.
2. Implement the new path.
3. Validate through syntax checks and smoke tests.
4. Replace the previous runtime path after validation.
5. Avoid preserving inactive runtime branches inside the repo.

## Reasoning

The ORIS project prioritizes:
- execution clarity
- operational simplicity
- low cognitive overhead
- easier AI self-maintenance
- faster debugging and iteration

## Backup guidance

Preferred rollback methods:
- git revert
- git checkout
- external snapshot restore

Example external backup location:
- /opt/backups/oris_20260511.tar.gz

Backups are preferred outside the active repository tree.
