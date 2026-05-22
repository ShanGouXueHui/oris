# AI Dev Employee Multi-Project Governance

ORIS is the AI employee platform repository. It is responsible for orchestration, routing, provider governance, execution rules, diagnostics, and cross-project templates.

New business application code should live in separate GitHub repositories, not inside the ORIS repository.

## Repository roles

- ORIS: platform, routing, runtime rules, project registry, diagnostics.
- Product repositories: application code, product-specific docs, tests, deployment logic.

## Required preflight before file changes

Before changing files, the AI dev employee should identify:

- task type
- target project
- target repository
- target local path
- target branch
- allowed scope
- current working directory
- git status
- latest commit SHA

If the target project is not clear, the agent should not write into the default workspace.

## New project rule

A new product should be created as an independent GitHub repository under `/home/admin/projects/<project-name>`. ORIS may record the project in `orchestration/project_registry.json`, but product code should remain in the product repository.

## Existing project rule

For existing projects, resolve the repository and local path from `orchestration/project_registry.json`, then execute inside that project directory.

## Completion requirements

For a finished task, the agent should return:

- repository name
- local path
- commit SHA
- changed files
- smoke or test result
- uncommitted files intentionally left untouched

Returning only the branch name, such as `main`, is not enough.
