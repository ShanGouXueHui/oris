#!/usr/bin/env python3
"""Patch real product repair E2E runner precheck/reporting.

Fixes two validation-runner issues:
1. ORIS working tree precheck was too strict because historical untracked
   runtime logs/evidence can exist locally. For ORIS, require no tracked/staged
   modifications but allow untracked files.
2. Early SystemExit failures produced sparse reports. Capture the exception into
   the report before committing diagnostics.

Product repository precheck remains strict.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

ORIS_DIR = Path("/home/admin/projects/oris")
TARGET = ORIS_DIR / "scripts" / "dev_employee_run_real_product_repair_e2e.py"

OLD_GIT_STATUS = '''def git_status(path: Path) -> str:
    return run(["git", "status", "--short"], cwd=path).stdout
'''

NEW_GIT_STATUS = '''def git_status(path: Path) -> str:
    return run(["git", "status", "--short"], cwd=path).stdout


def git_tracked_status(path: Path) -> str:
    return run(["git", "status", "--short", "--untracked-files=no"], cwd=path).stdout
'''

OLD_REQUIRE = '''def require_clean_trees() -> None:
    oris_status = git_status(ORIS_DIR)
    product_status = git_status(PRODUCT_DIR)
    if oris_status:
        raise SystemExit(f"ERROR: ORIS working tree is not clean before E2E:\\n{oris_status}")
    if product_status:
        raise SystemExit(f"ERROR: product working tree is not clean before E2E:\\n{product_status}")
'''

NEW_REQUIRE = '''def require_clean_trees() -> None:
    # ORIS can legitimately contain old untracked runtime logs/evidence on host.
    # Require no tracked/staged ORIS modifications, but do not block on untracked
    # runtime noise.
    oris_tracked_status = git_tracked_status(ORIS_DIR)
    product_status = git_status(PRODUCT_DIR)
    if oris_tracked_status:
        raise SystemExit(f"ERROR: ORIS tracked working tree is not clean before E2E:\\n{oris_tracked_status}")
    if product_status:
        raise SystemExit(f"ERROR: product working tree is not clean before E2E:\\n{product_status}")
'''

OLD_FINALLY = '''    finally:
        restore_product_if_needed(success)
        report["finished_at"] = now_iso()
        report["final_product_status"] = git_status(PRODUCT_DIR)
        commit_report(report)
        run(["git", "log", "-1", "--oneline"], cwd=ORIS_DIR)
        print(json.dumps({"ok": report.get("ok"), "repair_task_id": REPAIR_TASK_ID}, ensure_ascii=False, indent=2))
    return 0 if report.get("ok") else 1
'''

NEW_TRY_EXCEPT_FINALLY = '''    except BaseException as exc:
        report["ok"] = False
        report["error_type"] = type(exc).__name__
        report["error"] = str(exc)
        raise
    finally:
        restore_product_if_needed(success)
        report.setdefault("ok", success)
        report["finished_at"] = now_iso()
        report["final_product_status"] = git_status(PRODUCT_DIR)
        report["final_oris_tracked_status"] = git_tracked_status(ORIS_DIR)
        commit_report(report)
        run(["git", "log", "-1", "--oneline"], cwd=ORIS_DIR)
        print(json.dumps({"ok": report.get("ok"), "repair_task_id": REPAIR_TASK_ID}, ensure_ascii=False, indent=2))
    return 0 if report.get("ok") else 1
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
    if "def git_tracked_status(" not in text:
        if OLD_GIT_STATUS not in text:
            raise SystemExit("ERROR: git_status marker not found")
        text = text.replace(OLD_GIT_STATUS, NEW_GIT_STATUS, 1)
        changed = True
    if OLD_REQUIRE in text:
        text = text.replace(OLD_REQUIRE, NEW_REQUIRE, 1)
        changed = True
    if 'except BaseException as exc:' not in text:
        if OLD_FINALLY not in text:
            raise SystemExit("ERROR: finally marker not found")
        text = text.replace(OLD_FINALLY, NEW_TRY_EXCEPT_FINALLY, 1)
        changed = True
    if changed:
        TARGET.write_text(text, encoding="utf-8")
        print("PATCHED real product repair E2E precheck/reporting")
    else:
        print("NO_CHANGE real product repair E2E runner already patched")
    run(["python3", "-m", "py_compile", "scripts/dev_employee_run_real_product_repair_e2e.py"])
    run(["git", "add", "scripts/dev_employee_run_real_product_repair_e2e.py"])
    staged = run(["git", "diff", "--cached", "--quiet"], check=False)
    if staged.returncode != 0:
        run(["git", "commit", "-m", "test(dev-employee): relax real product repair e2e oris precheck"])
        run(["git", "push", "origin", "main"])
    run(["git", "log", "-1", "--oneline"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
