from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

from .clock import utc_compact_stamp
from .context import discover_repo_root
from .engineering_scan import scan_repository_sources
from .git_evidence import EvidenceArtifact, publish_evidence_artifacts
from .process import run


def _git_state(repo_root: Path) -> tuple[str, str, str]:
    head = run(["git", "rev-parse", "HEAD"], cwd=repo_root)
    remote = run(
        ["git", "ls-remote", "--heads", "origin", "refs/heads/main"],
        cwd=repo_root,
        timeout=60,
    )
    status = run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=repo_root,
    )
    if head.returncode != 0 or remote.returncode != 0 or status.returncode != 0:
        return "", "", "git_state_unavailable"
    head_sha = head.stdout.strip()
    remote_sha = remote.stdout.split()[0] if remote.stdout.split() else ""
    if not head_sha or not remote_sha:
        return head_sha, remote_sha, "git_state_incomplete"
    if head_sha != remote_sha:
        return head_sha, remote_sha, "head_differs_from_remote_main"
    if status.stdout.strip():
        return head_sha, remote_sha, "tracked_worktree_not_clean"
    return head_sha, remote_sha, ""


def audit_code_state(repo_root: Path) -> tuple[dict[str, Any], str, str]:
    report = scan_repository_sources(repo_root)
    audited_commit, _, git_error = _git_state(repo_root)
    contract_error = str(report.get("contract_error") or git_error or "")
    report["contract_error"] = contract_error or None
    report["ok"] = bool(report.get("ok")) and not contract_error
    return report, audited_commit, contract_error


def _counts(report: dict[str, Any]) -> dict[str, int]:
    return {
        "DUPLICATE_BINDINGS": len(report["duplicate_bindings"]),
        "AUTHORITY_VIOLATIONS": len(report["authority_violations"]),
        "DUPLICATE_FUNCTION_BODIES": len(report["duplicate_function_bodies"]),
        "IMPORT_CYCLES": len(report["import_cycles"]),
        "OVERSIZED_MODULES": len(report["oversized_modules"]),
        "FORBIDDEN_HARDCODING": len(report["forbidden_hardcoding"]),
        "LEGACY_PATH_FINDINGS": len(report["legacy_path_findings"]),
    }


def _write_report(
    report: dict[str, Any],
    stamp: str,
    audited_commit: str,
    contract_error: str,
) -> tuple[Path, Path, str, str]:
    filename = f"code-first-audit-{stamp}"
    relative_log = f"logs/dev_employee/code_audit/{filename}.log"
    relative_json = f"logs/dev_employee/code_audit/{filename}.json"
    temp_root = Path(tempfile.mkdtemp(prefix=f"oris-code-audit-{stamp}-"))
    local_log = temp_root / f"{filename}.log"
    local_json = temp_root / f"{filename}.json"
    counts = _counts(report)
    result = (
        "CODE_AUDIT_PASS"
        if report.get("ok") and not contract_error
        else "CODE_AUDIT_FAILED"
    )
    payload = {
        "schema_version": 1,
        "checked_at": stamp,
        "audited_commit": audited_commit,
        "result": result,
        "counts": counts,
        "contract_error": contract_error or None,
        "files_scanned": report.get("files_scanned"),
        "python_architecture_files_scanned": report.get(
            "python_architecture_files_scanned"
        ),
        "findings": {
            "duplicate_bindings": report["duplicate_bindings"],
            "authority_violations": report["authority_violations"],
            "duplicate_function_bodies": report["duplicate_function_bodies"],
            "import_cycles": report["import_cycles"],
            "oversized_modules": report["oversized_modules"],
            "forbidden_hardcoding": report["forbidden_hardcoding"],
            "legacy_path_findings": report["legacy_path_findings"],
        },
        "safety": {
            "openclaw_accessed": False,
            "gateway_restarted": False,
            "task_submitted": False,
        },
    }
    local_json.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    lines = [
        f"checked_at={stamp}",
        f"audited_commit={audited_commit}",
        f"result={result}",
        *[f"{key.lower()}={value}" for key, value in counts.items()],
        f"contract_error={contract_error}",
        "openclaw_accessed=NO",
        "gateway_restarted=NO",
        "task_submitted=NO",
    ]
    local_log.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return local_log, local_json, relative_log, relative_json


def _publish_report(
    repo_root: Path,
    stamp: str,
    local_log: Path,
    local_json: Path,
    relative_log: str,
    relative_json: str,
) -> str:
    return publish_evidence_artifacts(
        repo_root,
        local_log.parent,
        (
            EvidenceArtifact(relative_log, local_log),
            EvidenceArtifact(relative_json, local_json),
        ),
        f"chore(dev-employee): record code-first audit {stamp}",
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--publish-evidence", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    return parser


def main() -> int:
    args = _parser().parse_args()
    repo_root = discover_repo_root()
    stamp = utc_compact_stamp()
    report, audited_commit, contract_error = audit_code_state(repo_root)
    counts = _counts(report)
    local_log, local_json, relative_log, relative_json = _write_report(
        report,
        stamp,
        audited_commit,
        contract_error,
    )

    evidence_commit = ""
    if args.publish_evidence:
        try:
            evidence_commit = _publish_report(
                repo_root,
                stamp,
                local_log,
                local_json,
                relative_log,
                relative_json,
            )
        except Exception as exc:
            contract_error = f"evidence_publish_failed:{type(exc).__name__}"
            report["ok"] = False

    result = "CODE_AUDIT_PASS" if report["ok"] else "CODE_AUDIT_FAILED"
    if not args.quiet:
        print("===== SUMMARY =====")
        print(f"RESULT={result}")
        for key, value in counts.items():
            print(f"{key}={value}")
        print(f"CONTRACT_ERROR={contract_error}")
        print(f"AUDITED_COMMIT={audited_commit}")
        print(f"EVIDENCE_LOG={relative_log if args.publish_evidence else ''}")
        print(f"EVIDENCE_JSON={relative_json if args.publish_evidence else ''}")
        print(f"EVIDENCE_COMMIT={evidence_commit}")
        print("OPENCLAW_ACCESSED=NO")
        print("GATEWAY_RESTARTED=NO")
        print("TASK_SUBMITTED=NO")
        print(
            "NEXT_ACTION="
            + (
                "RUN_EFFECTIVE_SURFACE_DIAGNOSTIC"
                if report["ok"]
                else "FIX_ALL_CODE_AUDIT_FINDINGS"
            )
        )
        print("SEND_TO_CHAT=THIS_SUMMARY_ONLY")
        print("===== END SUMMARY =====")
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
