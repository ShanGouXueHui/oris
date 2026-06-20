from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from .process import run


@dataclass(frozen=True)
class EvidenceArtifact:
    relative_path: str
    source_path: Path


def _safe_relative_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise RuntimeError("evidence path must remain repository-relative")
    return path


def publish_evidence_artifacts(
    repo_root: Path,
    temp_root: Path,
    artifacts: tuple[EvidenceArtifact, ...],
    commit_message: str,
) -> str:
    if not artifacts:
        raise RuntimeError("at least one evidence artifact is required")
    if not commit_message.strip():
        raise RuntimeError("evidence commit message is required")

    normalized = tuple(
        EvidenceArtifact(
            _safe_relative_path(item.relative_path).as_posix(),
            item.source_path,
        )
        for item in artifacts
    )
    if len({item.relative_path for item in normalized}) != len(normalized):
        raise RuntimeError("duplicate evidence destination path")
    if any(not item.source_path.is_file() for item in normalized):
        raise RuntimeError("evidence source artifact is missing")

    fetched = run(["git", "fetch", "origin", "main"], cwd=repo_root, timeout=90)
    if fetched.returncode != 0:
        raise RuntimeError("unable to fetch ORIS main for evidence")

    worktree = temp_root / "evidence-worktree"
    added = run(
        ["git", "worktree", "add", "--detach", str(worktree), "origin/main"],
        cwd=repo_root,
        timeout=90,
    )
    if added.returncode != 0:
        raise RuntimeError("unable to create detached evidence worktree")

    try:
        destinations: list[str] = []
        for artifact in normalized:
            destination = worktree / artifact.relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(artifact.source_path, destination)
            destinations.append(artifact.relative_path)

        staged = run(["git", "add", "--", *destinations], cwd=worktree)
        checked = run(["git", "diff", "--cached", "--check"], cwd=worktree)
        if staged.returncode != 0 or checked.returncode != 0:
            raise RuntimeError("evidence staging validation failed")

        committed = run(
            ["git", "commit", "-m", commit_message],
            cwd=worktree,
            timeout=90,
        )
        if committed.returncode != 0:
            raise RuntimeError("evidence commit failed")

        refreshed = run(["git", "fetch", "origin", "main"], cwd=worktree, timeout=90)
        if refreshed.returncode != 0:
            raise RuntimeError("evidence refetch failed")
        merge_base = run(["git", "merge-base", "HEAD", "origin/main"], cwd=worktree)
        remote_ref = run(["git", "rev-parse", "origin/main"], cwd=worktree)
        if merge_base.returncode != 0 or remote_ref.returncode != 0:
            raise RuntimeError("evidence remote baseline lookup failed")
        if merge_base.stdout.strip() != remote_ref.stdout.strip():
            rebased = run(["git", "rebase", "origin/main"], cwd=worktree, timeout=90)
            if rebased.returncode != 0:
                raise RuntimeError("evidence rebase failed")

        commit = run(["git", "rev-parse", "HEAD"], cwd=worktree)
        pushed = run(["git", "push", "origin", "HEAD:main"], cwd=worktree, timeout=120)
        if commit.returncode != 0 or pushed.returncode != 0:
            raise RuntimeError("evidence push failed")

        remote = run(
            ["git", "ls-remote", "--heads", "origin", "refs/heads/main"],
            cwd=worktree,
            timeout=60,
        )
        remote_sha = remote.stdout.split()[0] if remote.stdout.split() else ""
        commit_sha = commit.stdout.strip()
        if remote.returncode != 0 or not commit_sha or remote_sha != commit_sha:
            raise RuntimeError("evidence remote SHA mismatch")
        return commit_sha
    finally:
        run(
            ["git", "worktree", "remove", "--force", str(worktree)],
            cwd=repo_root,
        )
