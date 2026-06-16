#!/usr/bin/env python3
"""Prepare and validate a three-way recovery of one stashed source file.

This helper is intentionally non-destructive: it never writes the repository,
changes refs, or drops a stash. It exports base/stash/origin/worktree versions,
performs a three-way merge, validates the merged shell script, and emits a
machine-readable result for the guarded shell orchestration layer.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any


def run(*args: str, cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False)
    if check and completed.returncode != 0:
        raise RuntimeError(f"command failed ({completed.returncode}): {' '.join(args)}")
    return completed


def git_bytes(repo: Path, spec: str) -> bytes:
    completed = subprocess.run(
        ["git", "show", spec],
        cwd=repo,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"git show failed: {spec}")
    return completed.stdout


def write_private(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    os.chmod(path, 0o600)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--stash-commit", required=True)
    parser.add_argument("--source-file", required=True)
    parser.add_argument("--archive-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    archive = Path(args.archive_dir).resolve()
    output = Path(args.output).resolve()
    source = args.source_file
    stash = args.stash_commit
    archive.mkdir(parents=True, exist_ok=True)
    os.chmod(archive, 0o700)

    versions = {
        "base": git_bytes(repo, f"{stash}^1:{source}"),
        "stash": git_bytes(repo, f"{stash}:{source}"),
        "origin": git_bytes(repo, f"origin/main:{source}"),
        "worktree": (repo / source).read_bytes(),
    }
    paths: dict[str, Path] = {}
    for name, data in versions.items():
        path = archive / f"{name}.sh"
        write_private(path, data)
        paths[name] = path

    merged = archive / "merged.sh"
    completed = subprocess.run(
        ["git", "merge-file", "-p", str(paths["origin"]), str(paths["base"]), str(paths["stash"])],
        cwd=repo,
        capture_output=True,
        check=False,
    )
    write_private(merged, completed.stdout)
    if completed.returncode == 1:
        result = {"result": "CONFLICT", "merge_returncode": 1}
        output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        return 2
    if completed.returncode != 0:
        raise RuntimeError(f"git merge-file failed: {completed.returncode}")

    syntax = subprocess.run(["bash", "-n", str(merged)], text=True, capture_output=True, check=False)
    text = merged.read_text(encoding="utf-8")
    if syntax.returncode != 0:
        raise RuntimeError("merged shell script failed bash -n")
    if "===== SUMMARY =====" not in text or "SEND_TO_CHAT=THIS_SUMMARY_ONLY" not in text:
        raise RuntimeError("merged source is missing the required summary contract")

    hashes = {name: digest(path) for name, path in paths.items()}
    hashes["merged"] = digest(merged)
    if hashes["worktree"] == hashes["origin"]:
        worktree_class = "matches_origin"
    elif hashes["worktree"] == hashes["stash"]:
        worktree_class = "matches_stash"
    elif hashes["worktree"] == hashes["base"]:
        worktree_class = "matches_base"
    elif hashes["worktree"] == hashes["merged"]:
        worktree_class = "matches_merged"
    else:
        worktree_class = "independent_variant"

    result: dict[str, Any] = {
        "result": "PASS",
        "source_file": source,
        "worktree_class": worktree_class,
        "merged_equals_origin": hashes["merged"] == hashes["origin"],
        "merged_equals_stash": hashes["merged"] == hashes["stash"],
        "hashes": hashes,
        "merged_path": str(merged),
        "archive_dir": str(archive),
        "bash_syntax": "PASS",
        "summary_contract": "PASS",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "hashes"}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
