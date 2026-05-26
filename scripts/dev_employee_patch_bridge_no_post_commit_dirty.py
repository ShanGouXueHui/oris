#!/usr/bin/env python3
"""Patch supervised bridge to avoid dirtying committed task evidence.

The bridge already commits ORIS evidence through commit_push_oris() and
commit_push_oris_failure(). After those commits, run_task()/fail_task() should
not rewrite orchestration/task_runs/<task_id>.json with extra runtime fields,
because that leaves the local tracked working tree dirty after every completed
or failed task.

Queue terminal files still keep the richer local task state under
orchestration/dev_employee_queue/*.done.json or *.failed.json.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

ORIS_DIR = Path("/home/admin/projects/oris")
TARGET = ORIS_DIR / "scripts" / "dev_employee_supervised_bridge_v2.py"

OLD_FAIL = '''    write_json(RUN_DIR / f"{task['task_id']}.json", task)
    failed_path = task_path.with_suffix(".failed.json")
'''
NEW_FAIL = '''    # Do not rewrite orchestration/task_runs/<task_id>.json after failure evidence
    # and triage commits; keep richer terminal runtime state only in the queue file.
    failed_path = task_path.with_suffix(".failed.json")
'''

OLD_SUCCESS = '''        task.update({"status": "completed", "product_result": product_result, "oris_result": oris_result, "finished_at": now_iso()})
        write_json(RUN_DIR / f"{task_id}.json", task)
        done_path = task_path.with_suffix(".done.json")
'''
NEW_SUCCESS = '''        task.update({"status": "completed", "product_result": product_result, "oris_result": oris_result, "finished_at": now_iso()})
        # Do not rewrite orchestration/task_runs/<task_id>.json after ORIS evidence
        # commit; keep richer terminal runtime state only in the queue file.
        done_path = task_path.with_suffix(".done.json")
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
    if OLD_FAIL in text:
        text = text.replace(OLD_FAIL, NEW_FAIL, 1)
        changed = True
    if OLD_SUCCESS in text:
        text = text.replace(OLD_SUCCESS, NEW_SUCCESS, 1)
        changed = True
    if not changed:
        print("NO_CHANGE bridge post-commit clean patch already applied")
    else:
        TARGET.write_text(text, encoding="utf-8")
        print("PATCHED bridge post-commit clean behavior")
    run(["python3", "-m", "py_compile", "scripts/dev_employee_supervised_bridge_v2.py"])
    run(["git", "add", "scripts/dev_employee_supervised_bridge_v2.py"])
    staged = run(["git", "diff", "--cached", "--quiet"], check=False)
    if staged.returncode != 0:
        run(["git", "commit", "-m", "fix(dev-employee): keep task evidence clean after bridge commit"])
        run(["git", "push", "origin", "main"])
    run(["git", "log", "-1", "--oneline"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
