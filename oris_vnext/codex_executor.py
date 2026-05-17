"""CodexExecutor scaffold for ORIS Dev Employee.

The executor is dry-run by default. Real Codex execution requires both a
config-level mode change and an explicit environment approval flag.
"""

from __future__ import annotations

import json
import os
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

    REAL_EXECUTION_MODES = {"real_execution_allowed", "approved_real_execution"}

    def __init__(self, runtime_config: dict[str, Any]) -> None:
        executor_config = runtime_config.get("executors", {}).get("codex_executor", {})
        self.command_name = str(executor_config.get("command", "codex"))
        self.default_mode = str(executor_config.get("default_mode", "dry_run_plan_only"))
        self.forbidden_shell_fragments = list(executor_config.get("forbidden_shell_fragments", []))
        self.approval_config = dict(executor_config.get("real_execution_approval", {}))
        log_dir = runtime_config.get("runtime", {}).get("default_log_dir", "run/dev_employee/logs")
        self.log_dir = Path(log_dir) / str(executor_config.get("log_subdir", "codex"))

    def build_command(self, prompt_path: str | Path) -> list[str]:
        return [self.command_name, "exec", "--input", str(prompt_path)]

    def validate_prompt_text(self, prompt_text: str) -> None:
        lowered = prompt_text.lower()
        blocked = [fragment for fragment in self.forbidden_shell_fragments if fragment.lower() in lowered]
        if blocked:
            raise ValueError(f"prompt contains forbidden shell fragment(s): {blocked}")

    def real_execution_mode_enabled(self) -> bool:
        return self.default_mode in self.REAL_EXECUTION_MODES

    def approval_env_var(self) -> str:
        return str(self.approval_config.get("env_var", "ORIS_CODEX_REAL_EXEC_APPROVED"))

    def approved_values(self) -> set[str]:
        raw_values = self.approval_config.get("approved_values", ["1", "true", "yes"])
        return {str(item).lower() for item in raw_values}

    def real_execution_approved(self) -> bool:
        env_var = self.approval_env_var()
        return os.getenv(env_var, "").lower() in self.approved_values()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _dry_run_result(
        self,
        *,
        command: list[str],
        started_at: str,
        reason: str,
        metadata: dict[str, Any] | None = None,
    ) -> ExecutorResult:
        return ExecutorResult(
            executor="codex_executor",
            command=command,
            dry_run=True,
            returncode=None,
            started_at=started_at,
            finished_at=self._now(),
            metadata={"reason": reason, **(metadata or {})},
        )

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

        if dry_run:
            return self._dry_run_result(
                command=command,
                started_at=started_at,
                reason="explicit_dry_run",
                metadata={"requested_real_execution": False},
            )

        if not self.real_execution_mode_enabled():
            return self._dry_run_result(
                command=command,
                started_at=started_at,
                reason="real_execution_disabled_by_config",
                metadata={
                    "requested_real_execution": True,
                    "default_mode": self.default_mode,
                    "required_modes": sorted(self.REAL_EXECUTION_MODES),
                },
            )

        if not self.real_execution_approved():
            return self._dry_run_result(
                command=command,
                started_at=started_at,
                reason="real_execution_approval_missing",
                metadata={
                    "requested_real_execution": True,
                    "approval_env_var": self.approval_env_var(),
                    "approved_values": sorted(self.approved_values()),
                },
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
                metadata={"requested_real_execution": True, "approval_env_var": self.approval_env_var()},
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
                metadata={"requested_real_execution": True, "approval_env_var": self.approval_env_var()},
            )


def write_executor_result(path: str | Path, result: ExecutorResult) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
