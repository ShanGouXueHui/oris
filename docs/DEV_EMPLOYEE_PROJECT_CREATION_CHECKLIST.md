# AI Dev Employee Project Creation Checklist

This checklist prevents new business projects from being created inside the ORIS platform repository.

## Before creating files

- Confirm `task_type = new_project`.
- Confirm project name and repository name.
- Confirm GitHub owner and repository URL.
- Confirm local path under `/home/admin/projects/<repo_name>`.
- Confirm whether repository creation is allowed.
- Confirm ORIS may only be modified for project registry and operational logs.

## Repository checks

- If the repository exists, clone it to the target local path.
- If the repository does not exist and creation is allowed, create it first.
- If the repository does not exist and creation is not allowed, stop and report.
- Never initialize product code inside `/home/admin/projects/oris`.

## Required initial files

- `README.md`
- `AGENTS.md`
- `docs/PROJECT_STATE.md`
- stack-specific minimal source skeleton
- minimal static check or smoke test

## ORIS registry update

When a new project is created, update `orchestration/project_registry.json` with:

- project key
- project name
- project type
- GitHub repository
- local path
- default branch
- allowed scope
- forbidden scope
- short notes

## Completion report

Return:

- product repository URL
- product local path
- product commit SHA
- changed files
- smoke or test result
- ORIS registry commit SHA, if the registry was updated

Do not return only `main` as the commit reference.
