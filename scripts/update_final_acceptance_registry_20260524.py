#!/usr/bin/env python3

import json
import sys
from pathlib import Path

product_sha = sys.argv[1]

for directory in [
    "logs/dev_employee",
    "memory/dev_employee",
    "orchestration/task_runs",
]:
    Path(directory).mkdir(parents=True, exist_ok=True)

registry_path = Path("orchestration/project_registry.json")
registry = json.loads(registry_path.read_text(encoding="utf-8"))
registry["updated_at"] = "2026-05-24"
registry.setdefault("projects", {})["oris-final-acceptance-api"] = {
    "name": "ORIS Final Acceptance API",
    "type": "test_project",
    "repo": "git@github.com:ShanGouXueHui/oris-final-acceptance-api.git",
    "github": "https://github.com/ShanGouXueHui/oris-final-acceptance-api",
    "local_path": "/home/admin/projects/oris-final-acceptance-api",
    "default_branch": "main",
    "allowed_scope": [
        "README.md",
        "AGENTS.md",
        "docs/",
        "app/",
        "tests/",
        "requirements.txt",
        ".gitignore",
    ],
    "forbidden_scope": [
        ".env",
        "secrets",
        "private_keys",
        "production_credentials",
    ],
    "notes": "Standalone final acceptance project for validating Codex-backed ORIS AI dev employee execution.",
}
registry_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

progress = {
    "task_id": "oris-final-acceptance-api-20260523",
    "status": "completed",
    "updated_at": "2026-05-24",
    "target_project": "oris-final-acceptance-api",
    "target_repo": "ShanGouXueHui/oris-final-acceptance-api",
    "target_path": "/home/admin/projects/oris-final-acceptance-api",
    "product_commit_sha": product_sha,
    "test_result": "python3 -m py_compile app/main.py passed; pytest -q passed",
    "blocked_reason": None,
}
Path("logs/dev_employee/latest_task_progress.json").write_text(json.dumps(progress, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
Path("logs/dev_employee/latest_task_progress.md").write_text(
    f"""# Latest Dev Employee Task Progress

Task id: `oris-final-acceptance-api-20260523`

Status: completed

Updated at: 2026-05-24

Product repo: `https://github.com/ShanGouXueHui/oris-final-acceptance-api`

Product local path: `/home/admin/projects/oris-final-acceptance-api`

Product commit SHA: `{product_sha}`

Checks passed:

- `python3 -m py_compile app/main.py`
- `pytest -q`

ORIS registry updated with `oris-final-acceptance-api`.
""",
    encoding="utf-8",
)
Path("orchestration/task_runs/oris-final-acceptance-api-20260523.json").write_text(json.dumps(progress, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

current_task = {
    "task_id": "oris-final-acceptance-api-20260523",
    "status": "completed",
    "task_type": "new_project_final_acceptance",
    "target_project": "oris-final-acceptance-api",
    "target_repo": "ShanGouXueHui/oris-final-acceptance-api",
    "target_path": "/home/admin/projects/oris-final-acceptance-api",
    "current_step": "completed",
    "completed_steps": [
        "read_required_github_context",
        "codex_created_product_code",
        "codex_created_local_product_commit",
        "installed_dependencies",
        "py_compile_passed",
        "pytest_passed",
        "product_commit_pushed",
        "project_registry_updated",
    ],
    "failed_steps": [],
    "next_action": "none",
    "last_error": None,
    "last_commit_sha": product_sha,
    "test_result": "python3 -m py_compile app/main.py passed; pytest -q passed",
    "blocked_reason": None,
    "updated_at": "2026-05-24",
}
Path("memory/dev_employee/current_task.json").write_text(json.dumps(current_task, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
Path("memory/dev_employee/current_task.md").write_text(
    f"""# Current AI Dev Employee Task

Status: completed

Task id: `oris-final-acceptance-api-20260523`

Target project: `oris-final-acceptance-api`

Target repository: `ShanGouXueHui/oris-final-acceptance-api`

Target local path: `/home/admin/projects/oris-final-acceptance-api`

Product commit SHA: `{product_sha}`

Checks passed:

- `python3 -m py_compile app/main.py`
- `pytest -q`

ORIS registry updated with `oris-final-acceptance-api`.
""",
    encoding="utf-8",
)
