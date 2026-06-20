from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class CommandResult:
    args: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str


def run(
    args: Sequence[str],
    *,
    cwd: Path | None = None,
    timeout: int | None = None,
) -> CommandResult:
    process = subprocess.run(
        list(args),
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    return CommandResult(tuple(args), process.returncode, process.stdout, process.stderr)
