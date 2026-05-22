# Existing Project Task Template

Use this template when asking the AI dev employee to work on an existing repository.

```text
Task type: existing_project
Target project: <project_key_in_project_registry>
Target local path: <expected_local_path>
Target repository: <github_repository>
Allowed scope: <paths_allowed_to_change>
Forbidden scope: .env, secrets, private keys, production credentials

Before changing files:
1. Read orchestration/project_registry.json.
2. Confirm target project metadata.
3. cd into the target local path.
4. Print pwd, git branch, git remote -v, git status --short, and latest commit SHA.
5. Stop if the local path or repository does not match the target project.

Task:
<describe the requested implementation>

Validation:
<describe static checks, smoke tests, or unit tests>

Completion:
1. Commit and push only the requested changes.
2. Return repository, local path, commit SHA, changed files, and test result.
3. Do not return only the branch name as commit ref.
```
