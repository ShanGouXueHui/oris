#!/usr/bin/env python3
"""Patch supervised bridge to run failure triage automatically.

This runner performs a small deterministic source patch on
scripts/dev_employee_supervised_bridge_v2.py, runs py_compile, then commits and
pushes the bridge change. It avoids committing runtime queue files.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

ORIS_DIR = Path("/home/admin/projects/oris")
BRIDGE = ORIS_DIR / "scripts" / "dev_employee_supervised_bridge_v2.py"

TRIAGE_FUNC = '''

def run_failure_triage(task_id: str) -> dict[str, Any]:
    script = ORIS_DIR / "scripts" / "dev_employee_failure_triage.py"
    log_path = LOG_DIR / f"{task_id}_failure_triage.txt"
    if not script.exists():
        return {"ok": False, "stage": "triage_script_missing", "script": str(script)}
    proc = run(["python3", str(script), "--task-id", task_id, "--commit"], cwd=ORIS_DIR, log_path=log_path)
    return {
        "ok": proc.returncode == 0,
        "return_code": proc.returncode,
        "log": str(log_path),
        "stdout_tail": proc.stdout[-2000:],
        "stderr_tail": proc.stderr[-2000:],
    }
'''

OLD_FAIL_SNIPPET = '''    evidence_result = commit_push_oris_failure(task, status, extra)
    task["failure_evidence_result"] = evidence_result
    if not evidence_result.get("ok"):
        task["oris_evidence_push_failed"] = True
    write_json(RUN_DIR / f"{task['task_id']}.json", task)
'''

NEW_FAIL_SNIPPET = '''    evidence_result = commit_push_oris_failure(task, status, extra)
    task["failure_evidence_result"] = evidence_result
    if not evidence_result.get("ok"):
        task["oris_evidence_push_failed"] = True
    triage_result = run_failure_triage(task["task_id"])
    task["failure_triage_result"] = triage_result
    if not triage_result.get("ok"):
        task["failure_triage_failed"] = True
    write_json(RUN_DIR / f"{task['task_id']}.json", task)
'''

DOC_OLD = '''- Failure paths must also persist GitHub-verifiable ORIS evidence whenever
  committing/pushing the ORIS repository is still possible.
'''

DOC_NEW = '''- Failure paths must also persist GitHub-verifiable ORIS evidence whenever
  committing/pushing the ORIS repository is still possible.
- Failure paths should also run deterministic failure triage so the next repair
  loop can proceed without asking the human for routine engineering decisions.
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
    text = BRIDGE.read_text(encoding="utf-8")
    changed = False

    if "def run_failure_triage(" not in text:
        marker = "\n\ndef fail_task("
        if marker not in text:
            raise SystemExit("ERROR: fail_task marker not found")
        text = text.replace(marker, TRIAGE_FUNC + marker, 1)
        changed = True

    if OLD_FAIL_SNIPPET in text and NEW_FAIL_SNIPPET not in text:
        text = text.replace(OLD_FAIL_SNIPPET, NEW_FAIL_SNIPPET, 1)
        changed = True

    if DOC_NEW not in text and DOC_OLD in text:
        text = text.replace(DOC_OLD, DOC_NEW, 1)
        changed = True

    if not changed:
        print("NO_CHANGE bridge already has failure triage integration")
    else:
        BRIDGE.write_text(text, encoding="utf-8")
        print("PATCHED bridge failure triage integration")

    run(["python3", "-m", "py_compile", "scripts/dev_employee_supervised_bridge_v2.py"])
    run(["git", "add", "scripts/dev_employee_supervised_bridge_v2.py"])
    staged = run(["git", "diff", "--cached", "--quiet"], check=False)
    if staged.returncode == 0:
        print("NO_COMMIT no staged bridge diff")
    else:
        run(["git", "commit", "-m", "feat(dev-employee): run failure triage from bridge"])
        run(["git", "push", "origin", "main"])
    run(["git", "log", "-1", "--oneline"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
