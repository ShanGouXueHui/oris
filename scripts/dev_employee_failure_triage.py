#!/usr/bin/env python3
"""Triage ORIS Dev Employee failure evidence.

Reads a committed/local task failure evidence JSON and writes deterministic
triage reports under logs/dev_employee/failure_triage/. The helper is intended
for the next autonomous repair loop: ORIS can inspect failure evidence from
GitHub/local checkout, classify the failure, summarize root cause, and decide
whether a routine autonomous rerun is safe.

This script does not modify product repositories or enqueue follow-up tasks.
Use --commit to persist the triage report into the ORIS repository.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ORIS_DIR = Path("/home/admin/projects/oris")
RUN_DIR = ORIS_DIR / "orchestration" / "task_runs"
LOG_DIR = ORIS_DIR / "logs" / "dev_employee"
TRIAGE_DIR = LOG_DIR / "failure_triage"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run(cmd: list[str], cwd: Path = ORIS_DIR) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True, check=False)


def resolve_failure_file(task_id: str) -> Path:
    failure = RUN_DIR / f"{task_id}.failure_result.json"
    if failure.exists():
        return failure
    fallback = RUN_DIR / f"{task_id}.json"
    if fallback.exists():
        return fallback
    raise SystemExit(f"ERROR: failure evidence not found for task_id={task_id}: {failure}")


def short_text(value: Any, limit: int = 500) -> str:
    text = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
    return text if len(text) <= limit else text[:limit] + "..."


def classify(evidence: dict[str, Any]) -> dict[str, Any]:
    status = str(evidence.get("status") or evidence.get("failure_stage") or "unknown")
    details = evidence.get("failure_details") if isinstance(evidence.get("failure_details"), dict) else {}

    if status == "blocked_skill_resolution_invalid":
        errors = evidence.get("skill_resolution_errors") or details.get("skill_resolution_errors") or []
        return {
            "category": "skill_resolution_enforcement",
            "root_cause": "; ".join(errors) or "Skill resolver evidence validation failed.",
            "routine_autonomous_repair_allowed": True,
            "recommended_action": "Inspect resolver report and Codex result skill_resolution; fix prompt/template/resolver copy behavior, then rerun with a new task id.",
            "repair_scope": "platform_prompt_or_resolver_contract",
        }

    if status == "blocked_result_schema_invalid":
        errors = evidence.get("schema_errors") or details.get("schema_errors") or []
        return {
            "category": "strict_result_schema",
            "root_cause": "; ".join(errors) or "Codex result JSON did not satisfy strict autonomous schema.",
            "routine_autonomous_repair_allowed": True,
            "recommended_action": "Fix autonomous prompt/template or result writer behavior so required strict fields are emitted, then rerun with a new task id.",
            "repair_scope": "platform_prompt_or_result_contract",
        }

    if status == "blocked_host_checks_failed":
        checks = evidence.get("checks") or details.get("checks") or {}
        failed = []
        for item in checks.get("results", []) if isinstance(checks, dict) else []:
            if isinstance(item, dict) and item.get("return_code") != 0:
                failed.append({"cmd": item.get("cmd"), "return_code": item.get("return_code"), "log": item.get("log")})
        return {
            "category": "host_checks_failed",
            "root_cause": f"Host-side verification failed for {len(failed)} check(s).",
            "routine_autonomous_repair_allowed": True,
            "recommended_action": "Inspect host check logs; fix product implementation/tests or environment issue according to log evidence, then rerun with a new task id.",
            "repair_scope": "product_or_test_environment",
            "failed_checks": failed,
        }

    if status == "codex_failed":
        return {
            "category": "codex_execution_failed",
            "root_cause": f"Codex process returned non-zero. Details: {short_text(details)}",
            "routine_autonomous_repair_allowed": True,
            "recommended_action": "Inspect Codex log and runtime descriptor; repair prompt/tooling/resource issue, then rerun with a new task id.",
            "repair_scope": "platform_execution",
        }

    if status == "bridge_exception":
        last_error = evidence.get("last_error") or details.get("last_error") or short_text(details)
        return {
            "category": "bridge_exception",
            "root_cause": str(last_error),
            "routine_autonomous_repair_allowed": True,
            "recommended_action": "Inspect bridge exception and local runtime setup; repair platform execution path, then rerun with a new task id.",
            "repair_scope": "platform_bridge",
        }

    if status in {"blocked_product_push_failed", "blocked_oris_push_failed"}:
        return {
            "category": "git_or_remote_verification",
            "root_cause": f"Git push or remote SHA verification failed at status={status}.",
            "routine_autonomous_repair_allowed": True,
            "recommended_action": "Inspect Git state, branch, push stderr, and remote SHA; fix synchronization/permissions then rerun or resume safely.",
            "repair_scope": "git_remote_state",
        }

    return {
        "category": "unknown_failure",
        "root_cause": f"Unclassified failure status={status}. Details: {short_text(details)}",
        "routine_autonomous_repair_allowed": False,
        "recommended_action": "Inspect full failure evidence manually before automated rerun.",
        "repair_scope": "unknown",
    }


def make_report(task_id: str, evidence_path: Path) -> dict[str, Any]:
    evidence = read_json(evidence_path)
    classification = classify(evidence)
    report = {
        "task_id": task_id,
        "triaged_at": now_iso(),
        "source_evidence": str(evidence_path),
        "status": evidence.get("status"),
        "strict_result_schema": evidence.get("strict_result_schema"),
        "classification": classification,
        "evidence_links": {
            "codex_log_path": evidence.get("codex_log_path"),
            "codex_result_path": evidence.get("codex_result_path"),
            "skill_resolver_report_json": evidence.get("skill_resolver_report_json"),
            "skill_resolver_report_markdown": evidence.get("skill_resolver_report_markdown"),
        },
        "next_step_contract": {
            "ask_human_for_routine_decision": False,
            "rerun_requires_new_task_id": True,
            "must_preserve_original_failure_evidence": True,
        },
    }
    return report


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    c = report["classification"]
    lines = [
        f"# Failure Triage — {report['task_id']}",
        "",
        f"Triaged at: `{report['triaged_at']}`",
        f"Status: `{report.get('status')}`",
        f"Category: `{c.get('category')}`",
        f"Repair scope: `{c.get('repair_scope')}`",
        f"Routine autonomous repair allowed: `{c.get('routine_autonomous_repair_allowed')}`",
        "",
        "## Root cause",
        "",
        str(c.get("root_cause")),
        "",
        "## Recommended action",
        "",
        str(c.get("recommended_action")),
        "",
        "## Evidence paths",
        "",
    ]
    for key, value in report.get("evidence_links", {}).items():
        lines.append(f"- {key}: `{value}`")
    if c.get("failed_checks"):
        lines.extend(["", "## Failed checks", ""])
        for item in c["failed_checks"]:
            lines.append(f"- `{item.get('cmd')}` -> return_code={item.get('return_code')}, log=`{item.get('log')}`")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def commit_reports(task_id: str, json_path: Path, md_path: Path) -> dict[str, Any]:
    files = [str(json_path.relative_to(ORIS_DIR)), str(md_path.relative_to(ORIS_DIR))]
    add = run(["git", "add", *files])
    if add.returncode != 0:
        return {"ok": False, "stage": "git_add", "stderr": add.stderr}
    staged = run(["git", "diff", "--cached", "--quiet"])
    if staged.returncode == 0:
        sha = run(["git", "rev-parse", "HEAD"]).stdout.strip()
        return {"ok": True, "committed": False, "commit_sha": sha}
    commit = run(["git", "commit", "-m", f"docs(dev-employee): triage failed task {task_id}"])
    if commit.returncode != 0:
        return {"ok": False, "stage": "git_commit", "stderr": commit.stderr}
    sha = run(["git", "rev-parse", "HEAD"]).stdout.strip()
    push = run(["git", "push", "origin", "main"])
    remote = run(["git", "ls-remote", "origin", "refs/heads/main"])
    remote_sha = remote.stdout.split()[0] if remote.returncode == 0 and remote.stdout.split() else None
    return {
        "ok": push.returncode == 0 and remote_sha == sha,
        "committed": True,
        "commit_sha": sha,
        "remote_sha": remote_sha,
        "push_stderr": push.stderr,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Triage ORIS Dev Employee failure evidence")
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--commit", action="store_true", help="commit and push triage reports to ORIS main")
    args = parser.parse_args()

    evidence_path = resolve_failure_file(args.task_id)
    report = make_report(args.task_id, evidence_path)
    json_path = TRIAGE_DIR / f"{args.task_id}.json"
    md_path = TRIAGE_DIR / f"{args.task_id}.md"
    write_json(json_path, report)
    write_markdown(md_path, report)

    output = {"ok": True, "report_json": str(json_path), "report_markdown": str(md_path), "triage": report}
    if args.commit:
        output["commit"] = commit_reports(args.task_id, json_path, md_path)
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if output.get("commit", {"ok": True}).get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
