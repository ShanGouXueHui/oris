#!/usr/bin/env python3
"""Generate or enqueue a repair task from failure triage evidence.

This helper reads:
- logs/dev_employee/failure_triage/<failed_task_id>.json
- orchestration/task_runs/<failed_task_id>.failure_result.json

It then builds a deterministic next repair task contract. By default it only
writes a repair plan under logs/dev_employee/repair_plans/. Use --enqueue to
submit the repair task through the existing loopback autonomous enqueue helper.

The helper does not modify product code and does not delete or overwrite the
original failure evidence.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ORIS_DIR = Path("/home/admin/projects/oris")
TRIAGE_DIR = ORIS_DIR / "logs" / "dev_employee" / "failure_triage"
REPAIR_PLAN_DIR = ORIS_DIR / "logs" / "dev_employee" / "repair_plans"
RUN_DIR = ORIS_DIR / "orchestration" / "task_runs"
ENQUEUE = ORIS_DIR / "scripts" / "dev_employee_autonomous_enqueue.py"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run(cmd: list[str], cwd: Path = ORIS_DIR) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True, check=False)
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, end="")
    return proc


def resolve_paths(failed_task_id: str) -> tuple[Path, Path]:
    triage = TRIAGE_DIR / f"{failed_task_id}.json"
    failure = RUN_DIR / f"{failed_task_id}.failure_result.json"
    if not triage.exists():
        raise SystemExit(f"ERROR: triage report not found: {triage}")
    if not failure.exists():
        raise SystemExit(f"ERROR: failure evidence not found: {failure}")
    return triage, failure


def infer_product_path(failure: dict[str, Any], override: str | None) -> str | None:
    if override:
        return override
    for candidate in [
        failure.get("product_path"),
        failure.get("failure_details", {}).get("codex_result", {}).get("product_path") if isinstance(failure.get("failure_details"), dict) else None,
        failure.get("codex_result", {}).get("product_path") if isinstance(failure.get("codex_result"), dict) else None,
    ]:
        if candidate:
            return str(candidate)
    codex_result_path = failure.get("codex_result_path")
    if codex_result_path:
        path = Path(str(codex_result_path))
        if path.exists():
            try:
                data = read_json(path)
                if data.get("product_path"):
                    return str(data["product_path"])
            except Exception:
                return None
    return None



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

def default_checks(product_path: str | None) -> list[str]:
    if not product_path:
        return []
    return [
        "python3 -m py_compile app/main.py",
        f"PYTHONPATH={product_path} {product_path}/.venv/bin/python -m pytest -q",
        f"PYTHONPATH={product_path} {product_path}/.venv/bin/python -m pytest -q -W error::DeprecationWarning",
    ]


def make_repair_contract(
    failed_task_id: str,
    new_task_id: str,
    triage: dict[str, Any],
    failure: dict[str, Any],
    product_path: str | None,
    product_repo: str,
) -> dict[str, Any]:
    classification = triage.get("classification") if isinstance(triage.get("classification"), dict) else {}
    category = classification.get("category", "unknown_failure")
    repair_scope = classification.get("repair_scope", "unknown")
    root_cause = classification.get("root_cause", "No root cause available")
    recommended_action = classification.get("recommended_action", "Inspect failure evidence and repair safely")

    objective = (
        f"Repair failed ORIS Dev Employee task `{failed_task_id}` using committed GitHub evidence and triage.\n\n"
        f"Failure category: {category}.\n"
        f"Repair scope: {repair_scope}.\n"
        f"Root cause summary: {root_cause}.\n"
        f"Recommended action: {recommended_action}.\n\n"
        "Required behavior:\n"
        "1. Read the original failure evidence JSON and triage JSON from ORIS repository.\n"
        "2. Inspect referenced logs and resolver reports before changing code.\n"
        "3. Preserve the original failure evidence; do not overwrite or delete it.\n"
        "4. Decide the minimal safe repair autonomously.\n"
        "5. Run the required checks and self-repair routine failures.\n"
        "6. Produce strict autonomous result schema with fresh skill resolver evidence."
    )

    constraints = [
        f"Original failed task id: {failed_task_id}.",
        f"Original failure evidence: orchestration/task_runs/{failed_task_id}.failure_result.json.",
        f"Failure triage report: logs/dev_employee/failure_triage/{failed_task_id}.json.",
        "Do not ask the human for routine engineering decisions.",
        "Do not overwrite or delete original failure evidence or triage reports.",
        "Use a new task id for the repair attempt.",
        "Respect ORIS repository/product repository separation.",
        "Do not commit .env, credentials, private keys, .venv, caches, browser profiles, or runtime queue JSON.",
    ]
    if product_path:
        constraints.append(f"Expected product path: {product_path}.")
    constraints.append(f"Repair scope from triage: {repair_scope}.")

    return {
        "failed_task_id": failed_task_id,
        "new_task_id": new_task_id,
        "created_at": now_iso(),
        "product_path": product_path,
        "product_repo": product_repo,
        "commit_message": f"fix(dev-employee): repair task {failed_task_id}",
        "objective": objective,
        "constraints": constraints,
        "checks": default_checks(product_path),
        "triage_category": category,
        "repair_scope": repair_scope,
        "source_evidence": failure.get("codex_log_path"),
        "routine_autonomous_repair_allowed": bool(classification.get("routine_autonomous_repair_allowed")),
        "next_step_contract": triage.get("next_step_contract", {}),
    }


def enqueue_repair(contract: dict[str, Any]) -> int:
    product_path = contract.get("product_path")
    if not product_path:
        raise SystemExit("ERROR: cannot enqueue repair without product_path; pass --product-path")
    cmd = [
        "python3",
        str(ENQUEUE),
        "--task-id",
        contract["new_task_id"],
        "--objective",
        contract["objective"],
        "--product-path",
        product_path,
        "--product-repo",
        contract["product_repo"],
        "--commit-message",
        contract["commit_message"],
        "--note",
        f"Repair task generated from triage of {contract['failed_task_id']}",
    ]
    for constraint in contract.get("constraints", []):
        cmd.extend(["--constraint", constraint])
    for check in contract.get("checks", []):
        cmd.extend(["--check", check])
    proc = run(cmd)
    return proc.returncode


def commit_plan(path: Path, failed_task_id: str) -> dict[str, Any]:
    rel = str(path.relative_to(ORIS_DIR))
    run(["git", "add", rel])
    staged = run(["git", "diff", "--cached", "--quiet"])
    if staged.returncode == 0:
        sha = run(["git", "rev-parse", "HEAD"]).stdout.strip()
        return {"ok": True, "committed": False, "commit_sha": sha}
    commit = run(["git", "commit", "-m", f"docs(dev-employee): plan repair for failed task {failed_task_id}"])
    if commit.returncode != 0:
        return {"ok": False, "stage": "commit", "return_code": commit.returncode}
    sha = run(["git", "rev-parse", "HEAD"]).stdout.strip()
    push = run(["git", "push", "origin", "main"])
    remote = run(["git", "ls-remote", "origin", "refs/heads/main"])
    remote_sha = remote.stdout.split()[0] if remote.returncode == 0 and remote.stdout.split() else None
    return {"ok": push.returncode == 0 and remote_sha == sha, "committed": True, "commit_sha": sha, "remote_sha": remote_sha}


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate or enqueue a repair task from ORIS failure triage")
    parser.add_argument("--failed-task-id", required=True)
    parser.add_argument("--new-task-id")
    parser.add_argument("--product-path")
    parser.add_argument("--product-repo", default="ShanGouXueHui/oris-final-acceptance-api")
    parser.add_argument("--allow-path-repo-mismatch", action="store_true", help="allow enqueue when product_path basename does not match product_repo slug; intended only for controlled fixture tests")
    parser.add_argument("--enqueue", action="store_true")
    parser.add_argument("--commit-plan", action="store_true")
    args = parser.parse_args()

    triage_path, failure_path = resolve_paths(args.failed_task_id)
    triage = read_json(triage_path)
    failure = read_json(failure_path)
    new_task_id = args.new_task_id or f"repair-{args.failed_task_id}"
    product_path = infer_product_path(failure, args.product_path)

    target_guard = enforce_target_guard(product_path, args.product_repo, args.enqueue, args.allow_path_repo_mismatch)
    contract = make_repair_contract(
        args.failed_task_id,
        new_task_id,
        triage,
        failure,
        product_path,
        args.product_repo,
    )
    contract["target_guard"] = target_guard
    plan_path = REPAIR_PLAN_DIR / f"{new_task_id}.json"
    write_json(plan_path, contract)

    output: dict[str, Any] = {"ok": True, "repair_plan": str(plan_path), "contract": contract}
    if args.commit_plan:
        output["commit"] = commit_plan(plan_path, args.failed_task_id)
    if args.enqueue:
        output["enqueue_return_code"] = enqueue_repair(contract)
        output["ok"] = output["enqueue_return_code"] == 0

    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if output.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
