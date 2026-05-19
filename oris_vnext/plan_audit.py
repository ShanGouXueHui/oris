"""Plan audit packet builder for ORIS Dev Employee."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AuditSignal:
    name: str
    ok: bool
    detail: str


@dataclass(frozen=True)
class PlanAuditPacket:
    ok: bool
    generated_at: str
    recommendation: str
    task_run_id: str | None
    request_summary: str | None
    objective: str | None
    mode: str | None
    readiness_status: str | None
    signals: list[AuditSignal] = field(default_factory=list)
    source_files: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "generated_at": self.generated_at,
            "recommendation": self.recommendation,
            "task_run_id": self.task_run_id,
            "request_summary": self.request_summary,
            "objective": self.objective,
            "mode": self.mode,
            "readiness_status": self.readiness_status,
            "signals": [asdict(signal) for signal in self.signals],
            "source_files": self.source_files,
            "metadata": self.metadata,
        }


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as fp:
        raw = json.load(fp)
    if not isinstance(raw, dict):
        raise ValueError(f"{path} must be a JSON object")
    return raw


def build_plan_audit_packet(
    *,
    task_binding_path: str | Path = "logs/dev_employee/latest_task_binding.json",
    packet_path: str | Path = "logs/dev_employee/latest_execution_packet.json",
    readiness_path: str | Path = "logs/dev_employee/latest_commercial_readiness.json",
    task_status_path: str | Path = "logs/dev_employee/latest_task_status.json",
) -> PlanAuditPacket:
    binding = load_json(task_binding_path)
    packet = load_json(packet_path)
    readiness = load_json(readiness_path)
    task_status = load_json(task_status_path)
    readiness_metadata = readiness.get("metadata", {}) if isinstance(readiness.get("metadata"), dict) else {}
    signals = [
        AuditSignal("task_binding_ok", binding.get("ok") is True, f"binding.ok={binding.get('ok')}"),
        AuditSignal("packet_ok", packet.get("ok") is True, f"packet.ok={packet.get('ok')}"),
        AuditSignal("readiness_green", readiness.get("status") == "green", f"readiness.status={readiness.get('status')}"),
        AuditSignal("task_reviewed", task_status.get("state") in {"reviewed", "approved_for_plan", "ready_for_execution_packet"}, f"task_status.state={task_status.get('state')}"),
        AuditSignal("safe_mode", packet.get("mode") == "dry_run_plan_only", f"mode={packet.get('mode')}"),
        AuditSignal("permission_closed", readiness_metadata.get("approval_allowed") is False, f"permission={readiness_metadata.get('approval_allowed')}"),
    ]
    ok = all(signal.ok for signal in signals)
    return PlanAuditPacket(
        ok=ok,
        generated_at=utc_now(),
        recommendation="plan_only_ok" if ok else "revise_or_block",
        task_run_id=binding.get("task_run_id"),
        request_summary=binding.get("request_summary"),
        objective=binding.get("objective"),
        mode=packet.get("mode"),
        readiness_status=readiness.get("status"),
        signals=signals,
        source_files={
            "task_binding": str(task_binding_path),
            "packet": str(packet_path),
            "readiness": str(readiness_path),
            "task_status": str(task_status_path),
        },
        metadata={
            "task_state": task_status.get("state"),
            "legacy_review_tracked_count": readiness_metadata.get("legacy_review_tracked_count"),
            "legacy_review_untracked_count": readiness_metadata.get("legacy_review_untracked_count"),
        },
    )


def write_audit_json(path: str | Path, packet: PlanAuditPacket) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(packet.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_audit_markdown(path: str | Path, packet: PlanAuditPacket) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Dev Employee Plan Audit Packet",
        "",
        f"- ok: `{packet.ok}`",
        f"- generated_at: `{packet.generated_at}`",
        f"- recommendation: `{packet.recommendation}`",
        f"- task_run_id: `{packet.task_run_id}`",
        f"- mode: `{packet.mode}`",
        f"- readiness_status: `{packet.readiness_status}`",
        f"- request_summary: {packet.request_summary}",
        f"- objective: {packet.objective}",
        "",
        "## Signals",
        "",
        "| Signal | OK | Detail |",
        "| --- | --- | --- |",
    ]
    for signal in packet.signals:
        lines.append(f"| `{signal.name}` | `{signal.ok}` | {signal.detail} |")
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
