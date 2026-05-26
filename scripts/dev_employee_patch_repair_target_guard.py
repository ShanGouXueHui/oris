#!/usr/bin/env python3
"""Patch repair-from-triage helper with product path/repo guard.

The guard prevents accidental enqueue of a repair task when the inferred
product_path appears to belong to a different local project than the target
product_repo. This is especially important for synthetic fixture failures.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

ORIS_DIR = Path("/home/admin/projects/oris")
TARGET = ORIS_DIR / "scripts" / "dev_employee_repair_from_triage.py"

INSERT_AFTER = '''def infer_product_path(failure: dict[str, Any], override: str | None) -> str | None:
'''

VALIDATION_FUNC = '''

def repo_slug(product_repo: str) -> str:
    return product_repo.rsplit("/", 1)[-1].strip()


def target_mismatch_reason(product_path: str | None, product_repo: str) -> str | None:
    if not product_path:
        return "missing product_path"
    slug = repo_slug(product_repo)
    if not slug:
        return "missing product_repo slug"
    path_name = Path(product_path).expanduser().name
    if path_name != slug:
        return f"product_path basename {path_name!r} does not match product_repo slug {slug!r}"
    return None


def enforce_target_guard(product_path: str | None, product_repo: str, enqueue: bool, allow_mismatch: bool) -> dict[str, Any]:
    reason = target_mismatch_reason(product_path, product_repo)
    result = {
        "product_path": product_path,
        "product_repo": product_repo,
        "mismatch_reason": reason,
        "enqueue_allowed": True,
        "guard_mode": "allow" if allow_mismatch else "strict",
    }
    if enqueue and reason and not allow_mismatch:
        raise SystemExit(
            "ERROR: refusing to enqueue repair task because product_path/product_repo mismatch: "
            f"{reason}. Pass explicit --product-path/--product-repo for the intended target or "
            "--allow-path-repo-mismatch for controlled fixture tests."
        )
    if reason and not allow_mismatch:
        result["enqueue_allowed"] = False
    return result
'''

OLD_CONTRACT_ARGS = '''    contract = make_repair_contract(
        args.failed_task_id,
        new_task_id,
        triage,
        failure,
        product_path,
        args.product_repo,
    )
'''

NEW_CONTRACT_ARGS = '''    target_guard = enforce_target_guard(product_path, args.product_repo, args.enqueue, args.allow_path_repo_mismatch)
    contract = make_repair_contract(
        args.failed_task_id,
        new_task_id,
        triage,
        failure,
        product_path,
        args.product_repo,
    )
    contract["target_guard"] = target_guard
'''

OLD_PARSER = '''    parser.add_argument("--product-repo", default="ShanGouXueHui/oris-final-acceptance-api")
    parser.add_argument("--enqueue", action="store_true")
'''

NEW_PARSER = '''    parser.add_argument("--product-repo", default="ShanGouXueHui/oris-final-acceptance-api")
    parser.add_argument("--allow-path-repo-mismatch", action="store_true", help="allow enqueue when product_path basename does not match product_repo slug; intended only for controlled fixture tests")
    parser.add_argument("--enqueue", action="store_true")
'''


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(cmd, cwd=str(ORIS_DIR), text=True, capture_output=True, check=False)
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, end="")
    if check and proc.returncode != 0:
        raise SystemExit(proc.returncode)
    return proc


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    changed = False

    if "def enforce_target_guard(" not in text:
        marker = "\ndef default_checks(product_path: str | None) -> list[str]:"
        if marker not in text:
            raise SystemExit("ERROR: default_checks marker not found")
        text = text.replace(marker, VALIDATION_FUNC + marker, 1)
        changed = True

    if OLD_PARSER in text and NEW_PARSER not in text:
        text = text.replace(OLD_PARSER, NEW_PARSER, 1)
        changed = True

    if OLD_CONTRACT_ARGS in text and "contract[\"target_guard\"] = target_guard" not in text:
        text = text.replace(OLD_CONTRACT_ARGS, NEW_CONTRACT_ARGS, 1)
        changed = True

    if not changed:
        print("NO_CHANGE repair target guard already applied")
    else:
        TARGET.write_text(text, encoding="utf-8")
        print("PATCHED repair target guard")

    run(["python3", "-m", "py_compile", "scripts/dev_employee_repair_from_triage.py"])
    run(["git", "add", "scripts/dev_employee_repair_from_triage.py"])
    staged = run(["git", "diff", "--cached", "--quiet"], check=False)
    if staged.returncode != 0:
        run(["git", "commit", "-m", "feat(dev-employee): guard triage repair target mismatch"])
        run(["git", "push", "origin", "main"])
    else:
        print("NO_COMMIT no staged diff")
    run(["git", "log", "-1", "--oneline"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
