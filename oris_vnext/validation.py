"""Validation pipeline scaffold for ORIS Dev Employee."""

from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ValidationCheckResult:
    name: str
    command: list[str]
    returncode: int
    started_at: str
    finished_at: str
    stdout: str = ""
    stderr: str = ""


@dataclass(frozen=True)
class ValidationReport:
    ok: bool
    checks: list[ValidationCheckResult]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "checks": [asdict(check) for check in self.checks],
            "metadata": self.metadata,
        }


class ValidationPipeline:
    """Run configured validation checks and preserve machine-readable results."""

    def __init__(self, runtime_config: dict[str, Any]) -> None:
        self.runtime_config = runtime_config
        executor_config = runtime_config.get("executors", {}).get("validation_pipeline", {})
        self.checks = list(executor_config.get("checks", []))

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def run(self, *, cwd: str | Path | None = None) -> ValidationReport:
        results: list[ValidationCheckResult] = []
        for raw_check in self.checks:
            name = str(raw_check["name"])
            command = [str(part) for part in raw_check["command"]]
            timeout_seconds = int(raw_check.get("timeout_seconds", 60))
            started_at = self._now()
            completed = subprocess.run(
                command,
                cwd=str(cwd) if cwd else None,
                text=True,
                capture_output=True,
                timeout=timeout_seconds,
                check=False,
            )
            results.append(
                ValidationCheckResult(
                    name=name,
                    command=command,
                    returncode=completed.returncode,
                    started_at=started_at,
                    finished_at=self._now(),
                    stdout=completed.stdout[-4000:],
                    stderr=completed.stderr[-4000:],
                )
            )
        return ValidationReport(ok=all(item.returncode == 0 for item in results), checks=results)


def load_runtime_config(path: str | Path = "config/dev_employee_runtime.json") -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as fp:
        raw = json.load(fp)
    if not isinstance(raw, dict):
        raise ValueError("runtime config must be a JSON object")
    return raw


def write_validation_report(path: str | Path, report: ValidationReport) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
