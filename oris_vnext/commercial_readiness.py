"""Commercial readiness evaluator for ORIS Dev Employee."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .execution_approval import evaluate_approval, load_approval, load_execution_packet


@dataclass(frozen=True)
class ReadinessGate:
    name: str
    ok: bool
    expected: Any
    actual: Any
    severity: str = "hard"


@dataclass(frozen=True)
class CommercialReadinessReport:
    generated_at: str
    status: str
    ok: bool
    gates: list[ReadinessGate] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "status": self.status,
            "ok": self.ok,
            "gates": [asdict(gate) for gate in self.gates],
            "metadata": self.metadata,
        }


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: str | Path) -> dict[str, Any]:
    target = Path(path)
    with target.open("r", encoding="utf-8") as fp:
        raw = json.load(fp)
    if not isinstance(raw, dict):
        raise ValueError(f"{target} must contain a JSON object")
    return raw


def artifact_exists(path: str | Path) -> bool:
    return Path(path).is_file()


def build_readiness_report(
    *,
    config_path: str | Path = "config/dev_employee_commercial_readiness.json",
    latest_index_path: str | Path = "logs/dev_employee/latest_cycle_index.json",
    planning_packet_path: str | Path = "logs/dev_employee/latest_planning_packet.json",
    execution_packet_path: str | Path = "logs/dev_employee/latest_execution_packet.json",
) -> CommercialReadinessReport:
    cfg = load_json(config_path)
    latest_index = load_json(latest_index_path)
    planning = load_json(planning_packet_path)
    execution = load_json(execution_packet_path)
    approval_result = evaluate_approval(
        approval=load_approval("config/dev_employee_execution_approval.json"),
        execution_packet=execution,
    )

    gates: list[ReadinessGate] = []
    for artifact in cfg.get("required_artifacts", []):
        gates.append(
            ReadinessGate(
                name=f"artifact_exists:{artifact}",
                ok=artifact_exists(artifact),
                expected=True,
                actual=artifact_exists(artifact),
            )
        )

    checks = {item.get("name"): item for item in latest_index.get("checks", []) if isinstance(item, dict)}
    for check_name in cfg.get("required_validation_checks", []):
        actual = checks.get(check_name, {}).get("result")
        gates.append(
            ReadinessGate(
                name=f"validation_check:{check_name}",
                ok=actual == "pass",
                expected="pass",
                actual=actual,
            )
        )

    hard = cfg.get("hard_gates", {}) if isinstance(cfg.get("hard_gates"), dict) else {}
    metadata = planning.get("metadata", {}) if isinstance(planning.get("metadata"), dict) else {}
    gates.extend(
        [
            ReadinessGate("latest_cycle_ok", latest_index.get("ok") is hard.get("latest_cycle_ok"), hard.get("latest_cycle_ok"), latest_index.get("ok")),
            ReadinessGate("bootstrap_ok", planning.get("bootstrap_ok") is hard.get("bootstrap_ok"), hard.get("bootstrap_ok"), planning.get("bootstrap_ok")),
            ReadinessGate("latest_validation_ok", planning.get("latest_validation_ok") is hard.get("latest_validation_ok"), hard.get("latest_validation_ok"), planning.get("latest_validation_ok")),
            ReadinessGate("blocking_dirty_tracked_count", metadata.get("blocking_dirty_tracked_count") == hard.get("blocking_dirty_tracked_count"), hard.get("blocking_dirty_tracked_count"), metadata.get("blocking_dirty_tracked_count")),
            ReadinessGate("blocking_untracked_count", metadata.get("blocking_untracked_count") == hard.get("blocking_untracked_count"), hard.get("blocking_untracked_count"), metadata.get("blocking_untracked_count")),
            ReadinessGate("execution_packet_mode", execution.get("mode") == hard.get("execution_packet_mode"), hard.get("execution_packet_mode"), execution.get("mode")),
            ReadinessGate("approval_enabled", approval_result.get("enabled") is hard.get("approval_enabled"), hard.get("approval_enabled"), approval_result.get("enabled")),
            ReadinessGate("real_execution_allowed", approval_result.get("allowed") is False, False, approval_result.get("allowed")),
        ]
    )

    ok = all(gate.ok for gate in gates if gate.severity == "hard")
    status = "green" if ok else "red"
    return CommercialReadinessReport(
        generated_at=utc_now(),
        status=status,
        ok=ok,
        gates=gates,
        metadata={
            "config_path": str(config_path),
            "latest_index_path": str(latest_index_path),
            "planning_packet_path": str(planning_packet_path),
            "execution_packet_path": str(execution_packet_path),
            "approval_allowed": approval_result.get("allowed"),
            "legacy_review_tracked_count": metadata.get("legacy_review_tracked_count"),
            "legacy_review_untracked_count": metadata.get("legacy_review_untracked_count"),
        },
    )


def write_readiness_json(path: str | Path, report: CommercialReadinessReport) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_readiness_markdown(path: str | Path, report: CommercialReadinessReport) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Dev Employee Commercial Readiness Report",
        "",
        f"- generated_at: `{report.generated_at}`",
        f"- status: `{report.status}`",
        f"- ok: `{report.ok}`",
        f"- approval_allowed: `{report.metadata.get('approval_allowed')}`",
        f"- legacy_review_tracked_count: `{report.metadata.get('legacy_review_tracked_count')}`",
        f"- legacy_review_untracked_count: `{report.metadata.get('legacy_review_untracked_count')}`",
        "",
        "| Gate | OK | Expected | Actual |",
        "| --- | --- | --- | --- |",
    ]
    for gate in report.gates:
        lines.append(f"| `{gate.name}` | `{gate.ok}` | `{gate.expected}` | `{gate.actual}` |")
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
