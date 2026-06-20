from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from .models import RuntimeContext
from .process import CommandResult, run
from .runtime_policy_patch import build_policy_validation_patch
from .state import sha256_file


_PATH_FLAGS = ("--config", "--config-path")
_DIRECT_VALIDATOR_CANDIDATES = (
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
    "policy",
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


def _patch_dry_run(
    context: RuntimeContext,
    candidate_path: Path,
    help_fingerprints: dict[str, dict[str, Any]],
    discovered: list[dict[str, Any]],
) -> dict[str, Any] | None:
    result, help_text = _help(("config", "patch"))
    help_fingerprints["config.patch"] = _fingerprint(result)
    required_flags = ("--file", "--dry-run")
    available = result.returncode == 0 and all(
        _contains_flag(help_text, flag) for flag in required_flags
    )
    discovery: dict[str, Any] = {
        "validator": "config.patch.dry-run",
        "available": available,
        "file_flag": _contains_flag(help_text, "--file"),
        "dry_run_flag": _contains_flag(help_text, "--dry-run"),
        "replace_path_flag": _contains_flag(help_text, "--replace-path"),
        "json_flag": _contains_flag(help_text, "--json"),
    }
    discovered.append(discovery)
    if not available:
        return None

    patch_path, replace_paths, patch_evidence = build_policy_validation_patch(
        context,
        candidate_path,
    )
    if replace_paths and not discovery["replace_path_flag"]:
        discovery["usable"] = False
        discovery["reason_code"] = "replace_path_flag_unavailable"
        return None

    command = [
        "openclaw",
        "config",
        "patch",
        "--file",
        str(patch_path),
        "--dry-run",
    ]
    for path in replace_paths:
        command.extend(["--replace-path", path])
    if discovery["json_flag"]:
        command.append("--json")

    before_sha = sha256_file(context.openclaw_config)
    validation = run(command, timeout=60)
    after_sha = sha256_file(context.openclaw_config)
    active_unchanged = before_sha == after_sha
    output = validation.stdout + "\n" + validation.stderr
    discovery["usable"] = True
    return {
        "status": (
            "PASS" if validation.returncode == 0 and active_unchanged else "FAIL"
        ),
        "reason_code": (
            None
            if validation.returncode == 0 and active_unchanged
            else "policy_patch_dry_run_rejected"
            if active_unchanged
            else "policy_patch_dry_run_modified_active_config"
        ),
        "validator": "config.patch.dry-run",
        "validation_scope": "minimal_policy_delta_against_active_config",
        "validation": _fingerprint(validation),
        "diagnostic_categories": _categories(output),
        "active_config_unchanged": active_unchanged,
        "active_config_written": False,
        "policy_patch": patch_evidence,
        "help_fingerprints": help_fingerprints,
        "discovered": discovered,
        "candidate_config_recorded": False,
        "secret_values_recorded": False,
    }


def _direct_candidate_validation(
    candidate_path: Path,
    root_help: str,
    help_fingerprints: dict[str, dict[str, Any]],
    discovered: list[dict[str, Any]],
) -> dict[str, Any] | None:
    for parts in _DIRECT_VALIDATOR_CANDIDATES:
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
        command = (
            ["openclaw", *parts, selected_flag, str(candidate_path)]
            if local_flag
            else ["openclaw", selected_flag, str(candidate_path), *parts]
        )
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
    return None


def validate_candidate_with_installed_runtime(
    context: RuntimeContext,
    candidate_path: Path,
) -> dict[str, Any]:
    root_result, root_help = _help(())
    help_fingerprints: dict[str, dict[str, Any]] = {
        "root": _fingerprint(root_result),
    }
    discovered: list[dict[str, Any]] = []

    patch_result = _patch_dry_run(
        context,
        candidate_path,
        help_fingerprints,
        discovered,
    )
    if patch_result is not None:
        return patch_result

    direct_result = _direct_candidate_validation(
        candidate_path,
        root_help,
        help_fingerprints,
        discovered,
    )
    if direct_result is not None:
        return direct_result

    return {
        "status": "NOT_CHECKED",
        "reason_code": "no_safe_candidate_validator_discovered",
        "help_fingerprints": help_fingerprints,
        "discovered": discovered,
        "candidate_config_recorded": False,
        "secret_values_recorded": False,
    }
