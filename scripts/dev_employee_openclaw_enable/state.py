from __future__ import annotations

import hashlib
from pathlib import Path

from .models import RepoSnapshot
from .process import run
from .task_contract import load_json_object as load_json


ACTIVE_QUEUE_SUFFIXES = {
    ".queued.json",
    ".running.json",
    ".claimed.json",
    ".planning.json",
    ".executing.json",
    ".committing.json",
    ".pushing.json",
    ".cancelling.json",
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def queue_directory(repo_root: Path) -> Path:
    return repo_root / "orchestration" / "dev_employee_queue"


def queue_fingerprint(repo_root: Path) -> str:
    root = queue_directory(repo_root)
    rows: list[str] = []
    if root.exists():
        for path in sorted(root.glob("*.json")):
            try:
                rows.append(f"{path.name}\t{sha256_file(path)}")
            except (FileNotFoundError, PermissionError):
                rows.append(f"{path.name}\t<unreadable>")
    return sha256_bytes("\n".join(rows).encode("utf-8"))


def active_queue_count(repo_root: Path) -> int:
    root = queue_directory(repo_root)
    if not root.exists():
        return 0
    return sum(
        1
        for path in root.glob("*.json")
        if any(path.name.endswith(suffix) for suffix in ACTIVE_QUEUE_SUFFIXES)
    )


def repository_snapshot(repo: Path) -> RepoSnapshot:
    head = run(["git", "rev-parse", "HEAD"], cwd=repo)
    remote = run(["git", "ls-remote", "--heads", "origin", "refs/heads/main"], cwd=repo)
    status = run(["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"], cwd=repo)
    tree = run(["git", "rev-parse", "HEAD^{tree}"], cwd=repo)
    if any(result.returncode != 0 for result in (head, remote, status, tree)):
        raise RuntimeError(f"unable to snapshot repository: {repo}")
    remote_sha = remote.stdout.split()[0] if remote.stdout.split() else ""
    return RepoSnapshot(
        head=head.stdout.strip(),
        remote_main=remote_sha,
        status_sha256=sha256_bytes(status.stdout.encode("utf-8")),
        tree=tree.stdout.strip(),
    )


def repository_is_clean(snapshot: RepoSnapshot) -> bool:
    return snapshot.status_sha256 == sha256_bytes(b"")


def repository_unchanged(before: RepoSnapshot, after: RepoSnapshot) -> bool:
    return before == after


def listener_is_loopback_only(port: int) -> bool:
    result = run(["ss", "-ltnH"])
    if result.returncode != 0:
        return False
    listeners: list[str] = []
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 4:
            local = parts[3]
            if local.endswith(f":{port}") or local.endswith(f"]:{port}"):
                listeners.append(local)
    return bool(listeners) and all(
        value.startswith("127.0.0.1:") or value.startswith("[::1]:")
        for value in listeners
    )
