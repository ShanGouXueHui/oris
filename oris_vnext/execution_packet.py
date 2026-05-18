"""Execution packet builder for ORIS Dev Employee.

This module converts a planning packet into a Codex-ready execution packet.
It does not execute Codex. It only materializes the prompt, approval metadata,
log paths, and safety constraints needed before execution can be considered.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ExecutionPacket:
    ok: bool
    generated_at: str
    mode: str
    approved_for_real_execution: bool
    task_summary: str
    objective: str
    planning_packet_path: str
    codex_prompt_path: str
    expected_outputs: list[str]
    constraints: list[str]
    safety_gates: dict[str, Any] = field(default_factory=dict)
    planning_snapshot: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as fp:
        raw = json.load(fp)
    if not isinstance(raw, dict):
        raise ValueError("input JSON must be an object")
    return raw


def render_codex_prompt(packet: ExecutionPacket) -> str:
    planning = packet.planning_snapshot
    metadata = planning.get("metadata", {}) if isinstance(planning.get("metadata"), dict) else {}
    latest = planning.get("latest_cycle_index", {}) if isinstance(planning.get("latest_cycle_index"), dict) else {}
    checks = latest.get("checks", []) if isinstance(latest.get("checks"), list) else []

    check_lines = []
    for check in checks:
        if isinstance(check, dict):
            check_lines.append(f"- {check.get('name')}: rc={check.get('returncode')} result={check.get('result')}")

    return "\n".join(
        [
            "# ORIS Dev Employee Execution Packet",
            "",
            "## Execution mode",
            "",
            f"- mode: {packet.mode}",
            f"- approved_for_real_execution: {packet.approved_for_real_execution}",
            "",
            "## Task",
            "",
            f"- summary: {packet.task_summary}",
            f"- objective: {packet.objective}",
            "",
            "## Current validation state",
            "",
            f"- latest_validation_ok: {planning.get('latest_validation_ok')}",
            f"- bootstrap_ok: {planning.get('bootstrap_ok')}",
            "",
            "## Validation checks",
            "",
            *(check_lines or ["- <none>"]),
            "",
            "## Worktree policy snapshot",
            "",
            f"- blocking_dirty_tracked_count: {metadata.get('blocking_dirty_tracked_count')}",
            f"- blocking_untracked_count: {metadata.get('blocking_untracked_count')}",
            f"- legacy_review_tracked_count: {metadata.get('legacy_review_tracked_count')}",
            f"- legacy_review_untracked_count: {metadata.get('legacy_review_untracked_count')}",
            "",
            "## Hard constraints",
            "",
            *[f"- {item}" for item in packet.constraints],
            "",
            "## Required behavior",
            "",
            "1. Read repository docs before proposing code changes.",
            "2. Do not use set -e in user-facing shell flows.",
            "3. Do not write secrets into files or logs.",
            "4. Keep changes small, reviewable, and validated.",
            "5. If execution is not explicitly approved, produce a plan only.",
            "",
        ]
    )


def build_execution_packet(
    *,
    planning_packet_path: str | Path = "logs/dev_employee/latest_planning_packet.json",
    output_dir: str | Path = "run/dev_employee/execution_packet",
    mode: str = "dry_run_plan_only",
    approved_for_real_execution: bool = False,
) -> ExecutionPacket:
    planning = load_json(planning_packet_path)
    output_dir = Path(output_dir)
    prompt_path = output_dir / "codex_prompt.md"
    packet = ExecutionPacket(
        ok=bool(planning.get("ok")) and not approved_for_real_execution,
        generated_at=utc_now(),
        mode=mode,
        approved_for_real_execution=approved_for_real_execution,
        task_summary=str(planning.get("task_summary", "Dev Employee execution packet")),
        objective=str(planning.get("objective", "Prepare a gated execution packet.")),
        planning_packet_path=str(planning_packet_path),
        codex_prompt_path=str(prompt_path),
        expected_outputs=[
            "codex_prompt.md",
            "execution_packet.json",
            "execution_packet.md",
        ],
        constraints=[
            "OpenClaw remains access/channel layer only.",
            "Real Codex execution is disabled by default.",
            "No secrets in files or logs.",
            "No set -e in user-facing shell flows.",
            "Small reversible changes only.",
            "Validate before commit/push.",
        ],
        safety_gates={
            "requires_planning_ok": True,
            "requires_bootstrap_ok": True,
            "requires_latest_validation_ok": True,
            "requires_explicit_real_execution_approval": True,
            "real_execution_default": "disabled",
        },
        planning_snapshot=planning,
    )
    return packet


def write_execution_packet(output_dir: str | Path, packet: ExecutionPacket) -> None:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    prompt_text = render_codex_prompt(packet)
    Path(packet.codex_prompt_path).parent.mkdir(parents=True, exist_ok=True)
    Path(packet.codex_prompt_path).write_text(prompt_text, encoding="utf-8")
    (output_dir / "execution_packet.json").write_text(
        json.dumps(packet.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "execution_packet.md").write_text(
        "# Dev Employee Execution Packet\n\n"
        f"- ok: `{packet.ok}`\n"
        f"- mode: `{packet.mode}`\n"
        f"- approved_for_real_execution: `{packet.approved_for_real_execution}`\n"
        f"- planning_packet_path: `{packet.planning_packet_path}`\n"
        f"- codex_prompt_path: `{packet.codex_prompt_path}`\n"
        "\n## Constraints\n\n"
        + "\n".join(f"- {item}" for item in packet.constraints)
        + "\n",
        encoding="utf-8",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a gated Dev Employee execution packet.")
    parser.add_argument("--planning-packet", default="logs/dev_employee/latest_planning_packet.json")
    parser.add_argument("--output-dir", default="run/dev_employee/execution_packet")
    parser.add_argument("--mode", default="dry_run_plan_only")
    parser.add_argument("--approve-real-execution", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    packet = build_execution_packet(
        planning_packet_path=args.planning_packet,
        output_dir=args.output_dir,
        mode=args.mode,
        approved_for_real_execution=args.approve_real_execution,
    )
    write_execution_packet(args.output_dir, packet)
    print(json.dumps({"ok": packet.ok, "mode": packet.mode, "codex_prompt_path": packet.codex_prompt_path}, ensure_ascii=False, sort_keys=True))
    return 0 if packet.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
