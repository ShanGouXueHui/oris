#!/usr/bin/env python3
"""Audit third-party OpenClaw/agent skill candidate repositories without executing them.

The script clones or refreshes candidate repos into a quarantine directory and
scans text files for manifests, install instructions, shell commands, network
calls, credential-sensitive paths, and package hooks. It does not execute any
candidate code.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ORIS_DIR = Path("/home/admin/projects/oris")
DEFAULT_CANDIDATES = ORIS_DIR / "orchestration" / "skill_candidates_20260525.json"
QUARANTINE_DIR = ORIS_DIR / "vendor" / "skill_candidates"
REPORT_DIR = ORIS_DIR / "logs" / "dev_employee" / "skill_audit"

TEXT_SUFFIXES = {
    ".md",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".py",
    ".js",
    ".ts",
    ".sh",
    ".bash",
    ".zsh",
    ".ps1",
    ".dockerfile",
}

RISK_PATTERNS = {
    "shell_download_exec": re.compile(r"(curl|wget).*(bash|sh|python|node)|bash\s+<\(|sh\s+<\(", re.I),
    "credential_keywords": re.compile(r"(api[_-]?key|secret|token|password|credential|private[_-]?key|ssh|\.env)", re.I),
    "sensitive_paths": re.compile(r"(\.ssh|\.gnupg|\.aws|\.config/gh|browser|wallet|keychain|secrets\.json)", re.I),
    "network_write": re.compile(r"(requests\.(post|put|delete)|fetch\(|axios\.|httpx\.(post|put|delete)|urllib\.request)", re.I),
    "process_exec": re.compile(r"(subprocess\.|os\.system|child_process|exec\(|spawn\(|eval\(|Function\()", re.I),
    "package_hooks": re.compile(r"(postinstall|preinstall|prepare|install\")", re.I),
}

MAX_FILE_BYTES = 256_000
MAX_FINDINGS_PER_KIND = 50


@dataclass
class Finding:
    kind: str
    path: str
    line: int
    text: str


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def slug_from_repo(repo_url: str) -> str:
    parsed = urlparse(repo_url)
    path = parsed.path.strip("/")
    if path.endswith(".git"):
        path = path[:-4]
    return path.replace("/", "__")


def run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, text=True, capture_output=True, check=False)


def clone_or_fetch(repo_url: str, target: Path) -> dict[str, Any]:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        result = run(["git", "fetch", "--all", "--prune"], cwd=target)
        reset = run(["git", "reset", "--hard", "origin/HEAD"], cwd=target)
        action = "fetched"
    else:
        result = run(["git", "clone", "--depth", "1", repo_url, str(target)])
        reset = run(["git", "status", "--short"], cwd=target) if result.returncode == 0 else result
        action = "cloned"
    sha = run(["git", "rev-parse", "HEAD"], cwd=target)
    remote = run(["git", "remote", "-v"], cwd=target)
    return {
        "action": action,
        "clone_return_code": result.returncode,
        "clone_stdout": result.stdout[-2000:],
        "clone_stderr": result.stderr[-2000:],
        "reset_return_code": reset.returncode,
        "commit_sha": sha.stdout.strip() if sha.returncode == 0 else None,
        "remote": remote.stdout.strip() if remote.returncode == 0 else None,
    }


def iter_text_files(root: Path):
    skip_dirs = {".git", "node_modules", ".venv", "venv", "dist", "build", ".next", ".cache"}
    for path in root.rglob("*"):
        if any(part in skip_dirs for part in path.parts):
            continue
        if not path.is_file():
            continue
        if path.name in {"Dockerfile", "Makefile"} or path.suffix.lower() in TEXT_SUFFIXES:
            if path.stat().st_size <= MAX_FILE_BYTES:
                yield path


def scan_repo(root: Path) -> dict[str, Any]:
    findings: list[Finding] = []
    manifests: list[str] = []
    install_files: list[str] = []
    file_count = 0
    scanned_count = 0

    for path in root.rglob("*"):
        if path.is_file():
            file_count += 1
            rel = path.relative_to(root).as_posix()
            if path.name in {"SKILL.md", "SOUL.md", "package.json", "pyproject.toml", "requirements.txt", "README.md"}:
                manifests.append(rel)

    for path in iter_text_files(root):
        scanned_count += 1
        rel = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if "install" in text.lower() or rel.lower() in {"readme.md", "skill.md"}:
            install_files.append(rel)
        for idx, line in enumerate(text.splitlines(), start=1):
            for kind, pattern in RISK_PATTERNS.items():
                if pattern.search(line):
                    if sum(1 for item in findings if item.kind == kind) < MAX_FINDINGS_PER_KIND:
                        findings.append(Finding(kind=kind, path=rel, line=idx, text=line.strip()[:240]))

    by_kind: dict[str, int] = {}
    for item in findings:
        by_kind[item.kind] = by_kind.get(item.kind, 0) + 1

    risk_score = min(100, sum(by_kind.values()))
    return {
        "file_count": file_count,
        "scanned_text_file_count": scanned_count,
        "manifest_files": sorted(set(manifests)),
        "install_related_files": sorted(set(install_files))[:100],
        "finding_counts": by_kind,
        "risk_score_rough": risk_score,
        "findings": [item.__dict__ for item in findings[:300]],
    }


def write_markdown(report_path: Path, data: dict[str, Any]) -> None:
    lines = [
        f"# Skill Candidate Audit — {data['candidate']['name']}",
        "",
        f"- Repo: `{data['candidate']['repo']}`",
        f"- Commit: `{data.get('commit_sha')}`",
        f"- Audit time: `{data['audited_at']}`",
        f"- Rough risk score: `{data['scan']['risk_score_rough']}`",
        "",
        "## Manifest files",
        "",
    ]
    for item in data["scan"]["manifest_files"][:50]:
        lines.append(f"- `{item}`")
    lines.extend(["", "## Finding counts", ""])
    for kind, count in sorted(data["scan"]["finding_counts"].items()):
        lines.append(f"- `{kind}`: {count}")
    lines.extend(["", "## Sample findings", ""])
    for item in data["scan"]["findings"][:80]:
        lines.append(f"- `{item['kind']}` `{item['path']}:{item['line']}` — `{item['text']}`")
    lines.append("")
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit skill candidate repositories without executing them")
    parser.add_argument("--candidates", default=str(DEFAULT_CANDIDATES))
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()

    candidates_path = Path(args.candidates)
    data = json.loads(candidates_path.read_text(encoding="utf-8"))
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)

    summary: dict[str, Any] = {
        "audited_at": now_iso(),
        "source": str(candidates_path),
        "policy": data.get("policy"),
        "reports": [],
    }

    for candidate in data.get("candidates", [])[: args.limit]:
        slug = slug_from_repo(candidate["repo"])
        target = QUARANTINE_DIR / slug
        clone_info = clone_or_fetch(candidate["repo"], target)
        scan = scan_repo(target) if clone_info["clone_return_code"] == 0 else {}
        report = {
            "audited_at": now_iso(),
            "candidate": candidate,
            "quarantine_path": str(target),
            "commit_sha": clone_info.get("commit_sha"),
            "clone_info": clone_info,
            "scan": scan,
            "decision": "quarantined_for_review_not_installed",
        }
        json_path = REPORT_DIR / f"{slug}.json"
        md_path = REPORT_DIR / f"{slug}.md"
        json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if scan:
            write_markdown(md_path, report)
        summary["reports"].append({
            "name": candidate["name"],
            "repo": candidate["repo"],
            "commit_sha": clone_info.get("commit_sha"),
            "json": str(json_path),
            "markdown": str(md_path),
            "risk_score_rough": scan.get("risk_score_rough") if scan else None,
            "finding_counts": scan.get("finding_counts") if scan else None,
        })

    summary_path = REPORT_DIR / "summary_20260525.json"
    summary_md_path = REPORT_DIR / "summary_20260525.md"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# Skill Candidate Audit Summary — 2026-05-25", "", "Downloaded to quarantine only. No candidate code executed.", ""]
    for item in summary["reports"]:
        lines.append(f"- **{item['name']}** `{item['commit_sha']}` rough risk `{item['risk_score_rough']}` — `{item['repo']}`")
    summary_md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"SUMMARY_JSON={summary_path}")
    print(f"SUMMARY_MD={summary_md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
