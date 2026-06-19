from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from .process import CommandResult, run


_PATH_FLAGS = ("--config", "--config-path")
_VALIDATOR_CANDIDATES = (
    ("config", "validate"),
    ("config", "check"),
)
_CATEGORY_TERMS = (
    "schema",
    "invalid",
    "unknown",
    "profile",
    "allow",
    "alsoallow",
    "deny",
    "group",
    "plugin",
    "tool",
)


def _fingerprint(result: CommandResult) -> dict[str, Any]:
    combined = (result.stdout + "\n" + result.stderr).encode("utf-8", errors="replace")
    return {
        "returncode": result.returncode,
        "stdout_bytes": len(result.stdout.encode("utf-8", errors="replace")),
        "stderr_bytes": len(result.stderr.encode("utf-8", errors="replace")),
        "output_sha256": hashlib.sha256(combined).hexdigest(),
    }


def _help(parts: tuple[str, ...]) -> tuple[CommandResult, str]:
    result = run(["openclaw", *parts, "--help"], timeout=30)
    return result, result.stdout + "\n" + result.stderr


def _contains_flag(help_text: str, flag: str) -> bool:
    return re.search(
        rf"(?<![A-Za-z0-9_-]){re.escape(flag)}(?![A-Za-z0-9_-])",
        help_text,
    ) is not None


def _categories(text: str) -> list[str]:
    lowered = text.lower().replace("_", "")
    return [term for term in _CATEGORY_TERMS if term in lowered]


def validate_candidate_with_installed_runtime(candidate_path: Path) -> dict[str, Any]:
    root_result, root_help = _help(())
    help_fingerprints: dict[str, dict[str, Any]] = {
        "root": _fingerprint(root_result),
    }
    discovered: list[dict[str, Any]] = []

    for parts in _VALIDATOR_CANDIDATES:
        result, help_text = _help(parts)
        name = ".".join(parts)
        help_fingerprints[name] = _fingerprint(result)
        if result.returncode != 0:
            continue
        local_flag = next(
            (flag for flag in _PATH_FLAGS if _contains_flag(help_text, flag)),
            None,
        )
        global_flag = next(
            (flag for flag in _PATH_FLAGS if _contains_flag(root_help, flag)),
            None,
        )
        selected_flag = local_flag or global_flag
        discovered.append(
            {
                "validator": name,
                "candidate_path_flag": selected_flag,
                "flag_scope": (
                    "local" if local_flag else "global" if global_flag else "none"
                ),
            }
        )
        if selected_flag is None:
            continue

        if local_flag:
            command = ["openclaw", *parts, selected_flag, str(candidate_path)]
        else:
            command = ["openclaw", selected_flag, str(candidate_path), *parts]
        validation = run(command, timeout=60)
        output = validation.stdout + "\n" + validation.stderr
        return {
            "status": "PASS" if validation.returncode == 0 else "FAIL",
            "validator": name,
            "candidate_path_flag": selected_flag,
            "flag_scope": "local" if local_flag else "global",
            "validation": _fingerprint(validation),
            "diagnostic_categories": _categories(output),
            "help_fingerprints": help_fingerprints,
            "discovered": discovered,
            "candidate_config_recorded": False,
            "secret_values_recorded": False,
        }

    return {
        "status": "NOT_CHECKED",
        "reason_code": "no_candidate_path_validator_discovered",
        "help_fingerprints": help_fingerprints,
        "discovered": discovered,
        "candidate_config_recorded": False,
        "secret_values_recorded": False,
    }
