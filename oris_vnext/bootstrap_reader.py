"""Repository bootstrap reader for ORIS Dev Employee.

The bootstrap reader verifies that configured continuity documents exist before
Dev Employee planning or execution begins. It is a guardrail, not a long-running
executor.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class BootstrapDocStatus:
    path: str
    exists: bool
    size_bytes: int | None = None


@dataclass(frozen=True)
class BootstrapReport:
    ok: bool
    checked_at: str
    repo_root: str
    worker_profile: str
    required_count: int
    missing_count: int
    docs: list[BootstrapDocStatus]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "checked_at": self.checked_at,
            "repo_root": self.repo_root,
            "worker_profile": self.worker_profile,
            "required_count": self.required_count,
            "missing_count": self.missing_count,
            "docs": [asdict(doc) for doc in self.docs],
            "metadata": self.metadata,
        }


class BootstrapReader:
    """Validate configured bootstrap docs for a worker profile."""

    def __init__(self, runtime_config: dict[str, Any], *, repo_root: str | Path = ".") -> None:
        self.runtime_config = runtime_config
        self.repo_root = Path(repo_root).resolve()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def verify(self, worker_profile: str = "dev_employee") -> BootstrapReport:
        profiles = self.runtime_config.get("worker_profiles", {})
        profile = profiles.get(worker_profile)
        if not isinstance(profile, dict):
            docs: list[BootstrapDocStatus] = []
            return BootstrapReport(
                ok=False,
                checked_at=self._now(),
                repo_root=str(self.repo_root),
                worker_profile=worker_profile,
                required_count=0,
                missing_count=1,
                docs=docs,
                metadata={"error": f"unknown worker profile: {worker_profile}"},
            )

        required_docs = [str(item) for item in profile.get("required_bootstrap_docs", [])]
        statuses: list[BootstrapDocStatus] = []
        for doc_path in required_docs:
            full_path = self.repo_root / doc_path
            exists = full_path.is_file()
            size_bytes = full_path.stat().st_size if exists else None
            statuses.append(BootstrapDocStatus(path=doc_path, exists=exists, size_bytes=size_bytes))

        missing_count = sum(1 for item in statuses if not item.exists)
        return BootstrapReport(
            ok=missing_count == 0,
            checked_at=self._now(),
            repo_root=str(self.repo_root),
            worker_profile=worker_profile,
            required_count=len(statuses),
            missing_count=missing_count,
            docs=statuses,
            metadata={"source": "config/dev_employee_runtime.json"},
        )


def load_runtime_config(path: str | Path = "config/dev_employee_runtime.json") -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as fp:
        raw = json.load(fp)
    if not isinstance(raw, dict):
        raise ValueError("runtime config must be a JSON object")
    return raw


def write_bootstrap_report(path: str | Path, report: BootstrapReport) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify ORIS Dev Employee bootstrap docs.")
    parser.add_argument("--config", default="config/dev_employee_runtime.json")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--worker-profile", default="dev_employee")
    parser.add_argument("--report", default="run/dev_employee/bootstrap_report.json")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = load_runtime_config(args.config)
    report = BootstrapReader(config, repo_root=args.repo_root).verify(args.worker_profile)
    write_bootstrap_report(args.report, report)
    print(json.dumps(report.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
