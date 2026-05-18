"""Worktree review exporter for ORIS Dev Employee planning packets."""

from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TrackedDiffReview:
    path: str
    diff_stat: str
    diff_text: str


@dataclass(frozen=True)
class WorktreeReview:
    generated_at: str
    planning_packet_path: str
    blocking_tracked_count: int
    blocking_untracked_count: int
    legacy_review_untracked_count: int
    tracked_diffs: list[TrackedDiffReview] = field(default_factory=list)
    blocking_untracked: list[str] = field(default_factory=list)
    legacy_review_untracked: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "planning_packet_path": self.planning_packet_path,
            "blocking_tracked_count": self.blocking_tracked_count,
            "blocking_untracked_count": self.blocking_untracked_count,
            "legacy_review_untracked_count": self.legacy_review_untracked_count,
            "tracked_diffs": [asdict(item) for item in self.tracked_diffs],
            "blocking_untracked": self.blocking_untracked,
            "legacy_review_untracked": self.legacy_review_untracked,
        }


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_packet(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as fp:
        raw = json.load(fp)
    if not isinstance(raw, dict):
        raise ValueError("planning packet must be a JSON object")
    return raw


def run_git(args: list[str], *, repo_root: str | Path = ".") -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=str(repo_root),
        text=True,
        capture_output=True,
        check=False,
    )
    return completed.stdout[-20000:]


def build_worktree_review(
    *,
    planning_packet_path: str | Path = "logs/dev_employee/latest_planning_packet.json",
    repo_root: str | Path = ".",
) -> WorktreeReview:
    packet = load_packet(planning_packet_path)
    metadata = packet.get("metadata", {}) if isinstance(packet.get("metadata"), dict) else {}
    blocking_tracked = [str(item) for item in metadata.get("blocking_dirty_tracked", [])]
    blocking_untracked = [str(item) for item in metadata.get("blocking_untracked", [])]
    legacy_review_untracked = [str(item) for item in metadata.get("legacy_review_untracked", [])]
    tracked_diffs: list[TrackedDiffReview] = []
    for path in blocking_tracked:
        tracked_diffs.append(
            TrackedDiffReview(
                path=path,
                diff_stat=run_git(["diff", "--stat", "--", path], repo_root=repo_root),
                diff_text=run_git(["diff", "--", path], repo_root=repo_root),
            )
        )
    return WorktreeReview(
        generated_at=utc_now(),
        planning_packet_path=str(planning_packet_path),
        blocking_tracked_count=len(blocking_tracked),
        blocking_untracked_count=len(blocking_untracked),
        legacy_review_untracked_count=len(legacy_review_untracked),
        tracked_diffs=tracked_diffs,
        blocking_untracked=blocking_untracked,
        legacy_review_untracked=legacy_review_untracked,
    )


def write_review_json(path: str | Path, review: WorktreeReview) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(review.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_review_markdown(path: str | Path, review: WorktreeReview) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Dev Employee Worktree Review",
        "",
        f"- generated_at: `{review.generated_at}`",
        f"- planning_packet_path: `{review.planning_packet_path}`",
        f"- blocking_tracked_count: `{review.blocking_tracked_count}`",
        f"- blocking_untracked_count: `{review.blocking_untracked_count}`",
        f"- legacy_review_untracked_count: `{review.legacy_review_untracked_count}`",
        "",
        "## Blocking tracked diffs",
        "",
    ]
    if not review.tracked_diffs:
        lines.extend(["```text", "<none>", "```", ""])
    for item in review.tracked_diffs:
        lines.extend(
            [
                f"### `{item.path}`",
                "",
                "Diff stat:",
                "",
                "```text",
                item.diff_stat.strip() or "<empty>",
                "```",
                "",
                "Diff:",
                "",
                "```diff",
                item.diff_text.strip() or "<empty>",
                "```",
                "",
            ]
        )
    lines.extend(["## Blocking untracked", "", "```text"])
    lines.append("\n".join(review.blocking_untracked) or "<none>")
    lines.extend(["```", "", "## Legacy review untracked", "", "```text"])
    lines.append("\n".join(review.legacy_review_untracked) or "<none>")
    lines.extend(["```", ""])
    target.write_text("\n".join(lines), encoding="utf-8")
