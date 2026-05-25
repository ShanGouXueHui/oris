# Skill Resolver Integration — 2026-05-26

## Purpose

Make capability selection part of the autonomous development loop instead of a manual afterthought.

## Required behavior

For every autonomous task, Codex must run the ORIS-owned skill resolver before editing product code:

```bash
python3 /home/admin/projects/oris/scripts/dev_employee_skill_resolver.py \
  --task-id <runtime_task_id> \
  --objective "<runtime_task_objective>"
```

If the objective mentions skills, OpenClaw, ClawHub, MCP, missing capabilities, external tools, downloading, or quarantine, Codex must use:

```bash
--quarantine
```

## Evidence

The resolver writes:

- `logs/dev_employee/skill_resolution/<task_id>.json`
- `logs/dev_employee/skill_resolution/<task_id>.md`

The final Codex result JSON must copy the resolver's `skill_resolution` object into its own `skill_resolution` field.

## Enforcement

The bridge already validates strict autonomous results. A strict autonomous task must include:

- `plan`
- `design_summary`
- `skill_resolution`
- `changed_files`
- `check_logs`
- `iteration_summary`
- `blockers`
- `notes`

Future enforcement should additionally verify that the referenced resolver report exists for strict autonomous tasks.

## Safety

External skill repositories remain untrusted. Resolver quarantine mode may mirror allowlisted intelligence repositories into:

`vendor/skill_candidates/`

It must not install, execute, or promote them into runtime automatically.
