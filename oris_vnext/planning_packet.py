"""Repo-aware planning packet builder for ORIS Dev Employee."""

from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .bootstrap_reader import BootstrapReader, load_runtime_config


DEFAULT_NON_BLOCKING_PREFIXES = ["logs/dev_employee/", "run/", "orchestration/"]
DEFAULT_NON_BLOCKING_FILES = ["memory/HANDOFF_VNEXT_LATEST.md"]


@dataclass(frozen=True)
class WorktreeStatus:
    dirty: bool
    tracked_modified: list[str]
    untracked: list[str]
    ignored_prefixes: list[str] = field(default_factory=list)
    ignored_files: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PlanningPacket:
    ok: bool
    generated_at: str
    repo_root: str
    worker_profile: str
    task_summary: str
    objective: str
    bootstrap_ok: bool
    latest_validation_ok: bool | None
    worktree: WorktreeStatus
    latest_cycle_index: dict[str, Any] = field(default_factory=dict)
    bootstrap_report: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "generated_at": self.generated_at,
            "repo_root": self.repo_root,
            "worker_profile": self.worker_profile,
            "task_summary": self.task_summary,
            "objective": self.objective,
            "bootstrap_ok": self.bootstrap_ok,
            "latest_validation_ok": self.latest_validation_ok,
            "worktree": asdict(self.worktree),
            "latest_cycle_index": self.latest_cycle_index,
            "bootstrap_report": self.bootstrap_report,
            "metadata": self.metadata,
        }


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json_if_exists(path: str | Path) -> dict[str, Any]:
    target = Path(path)
    if not target.exists():
        return {}
    with target.open("r", encoding="utf-8") as fp:
        raw = json.load(fp)
    return raw if isinstance(raw, dict) else {}


def is_non_blocking_path(path: str, *, prefixes: list[str], files: list[str]) -> bool:
    return path in files or any(path.startswith(prefix) for prefix in prefixes)


def collect_worktree_status(repo_root: str | Path = ".") -> WorktreeStatus:
    completed = subprocess.run(
        ["git", "status", "--short"],
        cwd=str(repo_root),
        text=True,
        capture_output=True,
        check=False,
    )
    tracked_modified: list[str] = []
    untracked: list[str] = []
    ignored_prefixes = list(DEFAULT_NON_BLOCKING_PREFIXES)
    ignored_files = list(DEFAULT_NON_BLOCKING_FILES)
    for line in completed.stdout.splitlines():
        if not line.strip():
            continue
        path = line[3:].strip() if len(line) > 3 else line.strip()
        status = line[:2]
        if status == "??":
            untracked.append(path)
        else:
            tracked_modified.append(path)
    return WorktreeStatus(
        dirty=bool(tracked_modified or untracked),
        tracked_modified=tracked_modified,
        untracked=untracked,
        ignored_prefixes=ignored_prefixes,
        ignored_files=ignored_files,
    )


def build_planning_packet(
    *,
    config_path: str | Path = "config/dev_employee_runtime.json",
    repo_root: str | Path = ".",
    worker_profile: str = "dev_employee",
    task_summary: str = "Dev Employee planning packet",
    objective: str = "Build a repo-aware planning input for the next Dev Employee iteration.",
    latest_index_path: str | Path = "logs/dev_employee/latest_cycle_index.json",
) -> PlanningPacket:
    config = load_runtime_config(config_path)
    bootstrap = BootstrapReader(config, repo_root=repo_root).verify(worker_profile)
    latest_index = load_json_if_exists(latest_index_path)
    latest_validation_ok = latest_index.get("ok") if latest_index else None
    worktree = collect_worktree_status(repo_root)
    blocking_dirty = [
        path
        for path in worktree.tracked_modified
        if not is_non_blocking_path(
            path,
            prefixes=worktree.ignored_prefixes,
            files=worktree.ignored_files,
        )
    ]
    ok = bool(bootstrap.ok) and latest_validation_ok is not False
    return PlanningPacket(
        ok=ok,
        generated_at=utc_now(),
        repo_root=str(Path(repo_root).resolve()),
        worker_profile=worker_profile,
        task_summary=task_summary,
        objective=objective,
        bootstrap_ok=bootstrap.ok,
        latest_validation_ok=latest_validation_ok if isinstance(latest_validation_ok, bool) else None,
        worktree=worktree,
        latest_cycle_index=latest_index,
        bootstrap_report=bootstrap.to_dict(),
        metadata={
            "blocking_dirty_tracked_count": len(blocking_dirty),
            "blocking_dirty_tracked": blocking_dirty,
            "policy": "dirty worktree is allowed for known runtime/generated files but must be visible before planning",
        },
    )


def write_packet_json(path: str | Path, packet: PlanningPacket) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(packet.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_packet_markdown(path: str | Path, packet: PlanningPacket) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    data = packet.to_dict()
    lines = [
        "# Dev Employee Planning Packet",
        "",
        f"- generated_at: `{data['generated_at']}`",
        f"- ok: `{data['ok']}`",
        f"- worker_profile: `{data['worker_profile']}`",
        f"- bootstrap_ok: `{data['bootstrap_ok']}`",
        f"- latest_validation_ok: `{data['latest_validation_ok']}`",
        f"- task_summary: {data['task_summary']}",
        f"- objective: {data['objective']}",
        "",
        "## Worktree",
        "",
        f"- dirty: `{data['worktree']['dirty']}`",
        f"- tracked_modified_count: `{len(data['worktree']['tracked_modified'])}`",
        f"- untracked_count: `{len(data['worktree']['untracked'])}`",
        f"- blocking_dirty_tracked_count: `{data['metadata']['blocking_dirty_tracked_count']}`",
        "",
        "### Blocking tracked changes",
        "",
        "```text",
        "\n".join(data['metadata']['blocking_dirty_tracked']) or "<none>",
        "```",
        "",
        "## Latest validation checks",
        "",
        "| Check | Return code | Result |",
        "| --- | ---: | --- |",
    ]
    for check in data.get("latest_cycle_index", {}).get("checks", []):
        lines.append(f"| `{check.get('name')}` | {check.get('returncode')} | {check.get('result')} |")
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a Dev Employee planning packet.")
    parser.add_argument("--config", default="config/dev_employee_runtime.json")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--worker-profile", default="dev_employee")
    parser.add_argument("--task-summary", default="Dev Employee planning packet")
    parser.add_argument("--objective", default="Build a repo-aware planning input for the next Dev Employee iteration.")
    parser.add_argument("--json-out", default="run/dev_employee/planning_packet.json")
    parser.add_argument("--md-out", default="run/dev_employee/planning_packet.md")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    packet = build_planning_packet(
        config_path=args.config,
        repo_root=args.repo_root,
        worker_profile=args.worker_profile,
        task_summary=args.task_summary,
        objective=args.objective,
    )
    write_packet_json(args.json_out, packet)
    write_packet_markdown(args.md_out, packet)
    print(json.dumps({"ok": packet.ok, "json_out": args.json_out, "md_out": args.md_out}, ensure_ascii=False, sort_keys=True))
    return 0 if packet.bootstrap_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
