# New Project Task Template

Use this template when asking the AI dev employee to create a new business project.

```text
Task type: new_project
Project name: <project_name>
GitHub repository: <owner>/<repo_name>
Local path: /home/admin/projects/<repo_name>
Allow creating new GitHub repo: yes/no
Allow modifying ORIS repo: only project_registry and dev_employee logs
Forbidden scope: .env, secrets, private keys, production credentials

Preflight:
1. Confirm this is a new product/project task, not an ORIS platform task.
2. Do not create application code under /home/admin/projects/oris.
3. Check whether the GitHub repository already exists.
4. Create or clone the repository under /home/admin/projects/<repo_name>.
5. Print pwd, git branch, git remote -v, git status --short, and latest commit SHA.
6. Stop if the working directory is not the target project repository.

Initial deliverables:
1. README.md
2. AGENTS.md
3. docs/PROJECT_STATE.md
4. Minimal source skeleton based on the requested stack
5. Basic smoke test or static check

ORIS registry update:
1. Add the new project to orchestration/project_registry.json.
2. Record repo, local_path, default_branch, allowed_scope, and forbidden_scope.
3. Commit registry/log updates in ORIS separately from product code if needed.

Completion:
1. Commit and push product code to the new project repository.
2. Return repository URL, local path, commit SHA, changed files, and smoke result.
3. If ORIS registry was updated, also return the ORIS commit SHA.
4. Do not return only the branch name as commit ref.
```
