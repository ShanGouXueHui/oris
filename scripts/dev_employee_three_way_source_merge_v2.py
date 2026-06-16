#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path


def git_show(repo, spec):
    proc = subprocess.run(
        ["git", "show", spec],
        cwd=str(repo),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError("git show failed: %s" % spec)
    return proc.stdout


def save(path, data, mode=0o600):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    os.chmod(str(path), mode)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
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
    os.chmod(str(archive), 0o700)

    specs = {
        "base": "%s^1:%s" % (stash, source),
        "stash": "%s:%s" % (stash, source),
        "origin": "origin/main:%s" % source,
    }
    paths = {}
    for name, spec in specs.items():
        path = archive / (name + ".sh")
        save(path, git_show(repo, spec))
        paths[name] = path

    worktree = archive / "worktree.sh"
    save(worktree, (repo / source).read_bytes())
    paths["worktree"] = worktree

    merge = subprocess.run(
        ["git", "merge-file", "-p", str(paths["origin"]), str(paths["base"]), str(paths["stash"])],
        cwd=str(repo),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    merged = archive / "merged.sh"
    save(merged, merge.stdout)
    if merge.returncode == 1:
        output.write_text(json.dumps({"result": "CONFLICT"}) + "\n", encoding="utf-8")
        return 2
    if merge.returncode != 0:
        raise RuntimeError("git merge-file failed")

    syntax = subprocess.run(["bash", "-n", str(merged)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if syntax.returncode != 0:
        raise RuntimeError("merged shell script failed bash -n")
    text = merged.read_text(encoding="utf-8")
    if "===== SUMMARY =====" not in text or "SEND_TO_CHAT=THIS_SUMMARY_ONLY" not in text:
        raise RuntimeError("merged source missing summary contract")

    hashes = {name: sha256(path) for name, path in paths.items()}
    hashes["merged"] = sha256(merged)
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

    result = {
        "result": "PASS",
        "worktree_class": worktree_class,
        "merged_equals_origin": hashes["merged"] == hashes["origin"],
        "merged_path": str(merged),
        "bash_syntax": "PASS",
        "summary_contract": "PASS",
    }
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
