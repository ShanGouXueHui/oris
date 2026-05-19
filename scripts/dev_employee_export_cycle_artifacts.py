#!/usr/bin/env python3
"""Export all fixed Dev Employee cycle artifacts.

This script centralizes generated GitHub-visible artifacts so the shell cycle
runner can remain small and maintainable.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from oris_vnext.commercial_readiness import (
    build_readiness_report,
    write_readiness_json,
    write_readiness_markdown,
)
from oris_vnext.execution_approval import (
    evaluate_approval,
    load_approval,
    write_approval_markdown,
    write_approval_result,
)
from oris_vnext.execution_packet import build_execution_packet, write_execution_packet
from oris_vnext.handoff_updater import render_handoff, write_handoff
from oris_vnext.log_summarizer import summarize_cycle_log, write_summary_json, write_summary_markdown
from oris_vnext.planning_packet import build_planning_packet, write_packet_json, write_packet_markdown
from oris_vnext.worktree_review import build_worktree_review, write_review_json, write_review_markdown


DEFAULT_PATHS = {
    "latest_index_json": "logs/dev_employee/latest_cycle_index.json",
    "latest_index_md": "logs/dev_employee/latest_cycle_index.md",
    "latest_handoff": "memory/HANDOFF_VNEXT_LATEST.md",
    "latest_packet_json": "logs/dev_employee/latest_planning_packet.json",
    "latest_packet_md": "logs/dev_employee/latest_planning_packet.md",
    "latest_worktree_review_json": "logs/dev_employee/latest_worktree_review.json",
    "latest_worktree_review_md": "logs/dev_employee/latest_worktree_review.md",
    "latest_execution_packet_json": "logs/dev_employee/latest_execution_packet.json",
    "latest_execution_packet_md": "logs/dev_employee/latest_execution_packet.md",
    "latest_codex_prompt": "logs/dev_employee/latest_codex_prompt.md",
    "latest_execution_approval_json": "logs/dev_employee/latest_execution_approval.json",
    "latest_execution_approval_md": "logs/dev_employee/latest_execution_approval.md",
    "latest_commercial_readiness_json": "logs/dev_employee/latest_commercial_readiness.json",
    "latest_commercial_readiness_md": "logs/dev_employee/latest_commercial_readiness.md",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export fixed Dev Employee cycle artifacts.")
    parser.add_argument("--summary-file", required=True)
    parser.add_argument("--run-dir", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    run_dir = Path(args.run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    summary = summarize_cycle_log(args.summary_file)
    write_summary_json(DEFAULT_PATHS["latest_index_json"], summary)
    write_summary_markdown(DEFAULT_PATHS["latest_index_md"], summary)
    write_handoff(DEFAULT_PATHS["latest_handoff"], render_handoff(summary.to_dict()))

    packet = build_planning_packet(
        task_summary="Dev Employee latest cycle planning packet",
        objective="Provide a single repo-aware planning input for the next Dev Employee iteration.",
    )
    write_packet_json(DEFAULT_PATHS["latest_packet_json"], packet)
    write_packet_markdown(DEFAULT_PATHS["latest_packet_md"], packet)

    review = build_worktree_review(planning_packet_path=DEFAULT_PATHS["latest_packet_json"])
    write_review_json(DEFAULT_PATHS["latest_worktree_review_json"], review)
    write_review_markdown(DEFAULT_PATHS["latest_worktree_review_md"], review)

    execution_dir = run_dir / "execution_packet"
    execution_packet = build_execution_packet(
        planning_packet_path=DEFAULT_PATHS["latest_packet_json"],
        output_dir=execution_dir,
    )
    write_execution_packet(execution_dir, execution_packet)
    shutil.copyfile(execution_dir / "execution_packet.json", DEFAULT_PATHS["latest_execution_packet_json"])
    shutil.copyfile(execution_dir / "execution_packet.md", DEFAULT_PATHS["latest_execution_packet_md"])
    shutil.copyfile(execution_dir / "codex_prompt.md", DEFAULT_PATHS["latest_codex_prompt"])

    approval_result = evaluate_approval(
        approval=load_approval("config/dev_employee_execution_approval.json"),
        execution_packet=execution_packet.to_dict(),
    )
    write_approval_result(DEFAULT_PATHS["latest_execution_approval_json"], approval_result)
    write_approval_markdown(DEFAULT_PATHS["latest_execution_approval_md"], approval_result)

    readiness = build_readiness_report()
    write_readiness_json(DEFAULT_PATHS["latest_commercial_readiness_json"], readiness)
    write_readiness_markdown(DEFAULT_PATHS["latest_commercial_readiness_md"], readiness)

    result = {
        "ok": True,
        "summary_file": args.summary_file,
        "run_dir": str(run_dir),
        "paths": DEFAULT_PATHS,
        "approval_allowed": approval_result.get("allowed"),
        "commercial_readiness_ok": readiness.ok,
        "commercial_readiness_status": readiness.status,
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
