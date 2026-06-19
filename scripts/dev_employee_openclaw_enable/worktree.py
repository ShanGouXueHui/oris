from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from .process import run


QUALITY_POLICY_PATH = Path("config/dev_employee/repository_quality_policy.json")


@dataclass(frozen=True)
class SourceWorktreeSnapshot:
    head: str
    remote_main: str
    tree: str
    dirty_count: int
    dirty_sha256: str


def _load_policy(repo_root: Path) -> dict:
    value = json.loads((repo_root / QUALITY_POLICY_PATH).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("repository quality policy must contain a JSON object")
    return value


def _configured_runtime_prefixes(repo_root: Path) -> tuple[str, ...]:
    policy = _load_policy(repo_root)
    values: list[str] = []
    for key in ("excluded_path_prefixes", "worktree_runtime_path_prefixes"):
        configured = policy.get(key, [])
        if not isinstance(configured, list) or not all(
            isinstance(item, str) for item in configured
        ):
            raise ValueError(f"repository quality policy {key} must be a string list")
        values.extend(configured)
    normalized = {
        value.strip().strip("/")
        for value in values
        if value.strip().strip("/")
    }
    return tuple(sorted(normalized))


def _decode_paths(raw: str) -> set[str]:
    return {
        value.replace("\\", "/").strip("/")
        for value in raw.split("\0")
        if value.strip("\0/")
    }


def _all_changed_paths(repo_root: Path) -> set[str]:
    commands = (
        ["git", "diff", "--name-only", "-z"],
        ["git", "diff", "--cached", "--name-only", "-z"],
        ["git", "ls-files", "--others", "--exclude-standard", "-z"],
    )
    paths: set[str] = set()
    for command in commands:
        result = run(command, cwd=repo_root)
        if result.returncode != 0:
            raise RuntimeError("unable to enumerate ORIS worktree changes")
        paths.update(_decode_paths(result.stdout))
    return paths


def _is_runtime_path(path: str, prefixes: tuple[str, ...]) -> bool:
    return any(path == prefix or path.startswith(prefix + "/") for prefix in prefixes)


def _source_dirty_paths(repo_root: Path) -> tuple[str, ...]:
    prefixes = _configured_runtime_prefixes(repo_root)
    return tuple(
        sorted(
            path
            for path in _all_changed_paths(repo_root)
            if not _is_runtime_path(path, prefixes)
        )
    )


def _git_value(repo_root: Path, arguments: list[str]) -> str:
    result = run(["git", *arguments], cwd=repo_root)
    if result.returncode != 0:
        raise RuntimeError("unable to resolve ORIS repository state")
    return result.stdout.strip()


def source_worktree_snapshot(repo_root: Path) -> SourceWorktreeSnapshot:
    dirty_paths = _source_dirty_paths(repo_root)
    dirty_payload = "\n".join(dirty_paths).encode("utf-8")
    remote = run(
        ["git", "ls-remote", "--heads", "origin", "refs/heads/main"],
        cwd=repo_root,
    )
    if remote.returncode != 0:
        raise RuntimeError("unable to resolve ORIS remote main")
    remote_main = remote.stdout.split()[0] if remote.stdout.split() else ""
    return SourceWorktreeSnapshot(
        head=_git_value(repo_root, ["rev-parse", "HEAD"]),
        remote_main=remote_main,
        tree=_git_value(repo_root, ["rev-parse", "HEAD^{tree}"]),
        dirty_count=len(dirty_paths),
        dirty_sha256=hashlib.sha256(dirty_payload).hexdigest(),
    )


def source_worktree_is_clean(snapshot: SourceWorktreeSnapshot) -> bool:
    return snapshot.dirty_count == 0


def source_worktree_is_synced(snapshot: SourceWorktreeSnapshot) -> bool:
    return bool(snapshot.remote_main) and snapshot.head == snapshot.remote_main


def source_worktree_unchanged(
    before: SourceWorktreeSnapshot,
    after: SourceWorktreeSnapshot,
) -> bool:
    return before == after
