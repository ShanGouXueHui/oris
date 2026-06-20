from __future__ import annotations

import hashlib
from typing import Any

from .process import CommandResult


def command_result_fingerprint(result: CommandResult) -> dict[str, Any]:
    combined = (result.stdout + "\n" + result.stderr).encode(
        "utf-8",
        errors="replace",
    )
    return {
        "returncode": result.returncode,
        "stdout_bytes": len(result.stdout.encode("utf-8", errors="replace")),
        "stderr_bytes": len(result.stderr.encode("utf-8", errors="replace")),
        "output_sha256": hashlib.sha256(combined).hexdigest(),
    }
