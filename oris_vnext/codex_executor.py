"""CodexExecutor scaffold for ORIS Dev Employee.

The executor is dry-run by default. It defines the command contract and log
shape without starting long-running or interactive coding work from channel
handlers.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ExecutorResult:
    executor: str
    command: list[str]
    dry_run: bool
    returncode: int | None
    started_at: str
    finished_at: str
    stdout_path: str | None = None
    stderr_path: str | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CodexExecutor:
    """Controlled wrapper around Codex CLI for Dev Employee tasks."""

    def __init__(self, runtime_config: dict[str, Any]) -> None:
        executor_config = runtime_config.get("executors", {}).get("codex_executor", {})
        self.command_name = str(executor_config.get("command", "codex"))
        self.default_mode = str(executor_config.get("default_mode", "dry_run_plan_only"))
        self.forbidden_shell_fragments = list(executor_config.get("forbidden_shell_fragments", []))
        log_dir = runtime_config.get("runtime", {}).get("default_log_dir", "run/dev_employee/logs")
        self.log_dir = Path(log_dir) / str(executor_config.get("log_subdir", "codex"))

    def build_command(self, prompt_path: str | Path) -> list[str]:
        return [self.command_name, "exec", "--input", str(prompt_path)]

    def validate_prompt_text(self, prompt_text: str) -> None:
        lowered = prompt_text.lower()
        blocked = [fragment for fragment in self.forbidden_shell_fragments if fragment.lower() in lowered]
        if blocked:
            raise ValueError(f"prompt contains forbidden shell fragment(s): {blocked}")

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def run(
        self,
        prompt_path: str | Path,
        *,
        dry_run: bool = True,
        cwd: str | Path | None = None,
        timeout_seconds: int = 900,
    ) -> ExecutorResult:
        prompt_path = Path(prompt_path)
        prompt_text = prompt_path.read_text(encoding="utf-8")
        self.validate_prompt_text(prompt_text)
        command = self.build_command(prompt_path)
        started_at = self._now()

        if dry_run or self.default_mode == "dry_run_plan_only":
            finished_at = self._now()
            return ExecutorResult(
                executor="codex_executor",
                command=command,
                dry_run=True,
                returncode=None,
                started_at=started_at,
                finished_at=finished_at,
                metadata={"reason": "dry_run_plan_only"},
            )

        self.log_dir.mkdir(parents=True, exist_ok=True)
        safe_started_at = started_at.replace(":", "").replace("+", "_")
        stdout_path = self.log_dir / f"codex_stdout_{safe_started_at}.log"
        stderr_path = self.log_dir / f"codex_stderr_{safe_started_at}.log"
        try:
            completed = subprocess.run(
                command,
                cwd=str(cwd) if cwd else None,
                text=True,
                capture_output=True,
                timeout=timeout_seconds,
                check=False,
            )
            stdout_path.write_text(completed.stdout, encoding="utf-8")
            stderr_path.write_text(completed.stderr, encoding="utf-8")
            return ExecutorResult(
                executor="codex_executor",
                command=command,
                dry_run=False,
                returncode=completed.returncode,
                started_at=started_at,
                finished_at=self._now(),
                stdout_path=str(stdout_path),
                stderr_path=str(stderr_path),
            )
        except Exception as exc:
            return ExecutorResult(
                executor="codex_executor",
                command=command,
                dry_run=False,
                returncode=None,
                started_at=started_at,
                finished_at=self._now(),
                error=repr(exc),
            )


def write_executor_result(path: str | Path, result: ExecutorResult) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
