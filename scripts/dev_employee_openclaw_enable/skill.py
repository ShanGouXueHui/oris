from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import RuntimeContext
from .process import run


@dataclass(frozen=True)
class SkillBackup:
    target_directory: Path
    backup_directory: Path
    existed_before: bool


def _skill_file(directory: Path) -> Path:
    return directory / "SKILL.md"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _managed_target(context: RuntimeContext) -> Path:
    root = context.managed_skills_root.resolve()
    target = (root / context.routing_skill_name).resolve()
    if root not in target.parents:
        raise RuntimeError("managed routing skill target escapes the skills root")
    return target


def validate_skill_cli() -> bool:
    install_help = run(
        ["openclaw", "skills", "install", "--help"],
        timeout=30,
    )
    info_help = run(
        ["openclaw", "skills", "info", "--help"],
        timeout=30,
    )
    if install_help.returncode != 0 or info_help.returncode != 0:
        return False
    install_text = install_help.stdout + "\n" + install_help.stderr
    info_text = info_help.stdout + "\n" + info_help.stderr
    return all(flag in install_text for flag in ("--as", "--global", "--force")) and "--json" in info_text


def backup_routing_skill(
    context: RuntimeContext,
    transaction_backup_directory: Path,
) -> SkillBackup:
    target = _managed_target(context)
    if target.is_symlink():
        raise RuntimeError("managed routing skill target must not be a symlink")
    backup_directory = transaction_backup_directory / "routing-skill-before"
    existed_before = target.exists()
    if existed_before:
        shutil.copytree(target, backup_directory, symlinks=True)
    return SkillBackup(target, backup_directory, existed_before)


def _find_path_strings(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for child in value.values():
            found.extend(_find_path_strings(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(_find_path_strings(child))
    elif isinstance(value, str) and ("/" in value or "\\" in value):
        found.append(value)
    return found


def _parse_json_output(value: str) -> Any | None:
    stripped = value.strip()
    if not stripped:
        return None
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            return json.loads(stripped[start : end + 1])
        except json.JSONDecodeError:
            return None


def _effective_skill_is_managed(
    context: RuntimeContext,
    info_output: str,
) -> bool:
    payload = _parse_json_output(info_output)
    if payload is None:
        return False
    target = _managed_target(context)
    expected = {str(target), str(_skill_file(target))}
    for value in _find_path_strings(payload):
        try:
            resolved = str(Path(value).expanduser().resolve())
        except Exception:
            continue
        if resolved in expected:
            return True
    return False


def install_routing_skill(context: RuntimeContext) -> dict[str, Any]:
    source_skill = _skill_file(context.routing_skill_source)
    target = _managed_target(context)
    arguments = [
        "openclaw",
        "skills",
        "install",
        str(context.routing_skill_source),
        "--as",
        context.routing_skill_name,
        "--global",
    ]
    if context.routing_skill_force_replace:
        arguments.append("--force")
    installed = run(arguments, cwd=context.repo_root, timeout=90)
    if installed.returncode != 0:
        raise RuntimeError("managed ORIS routing skill install failed")
    target_skill = _skill_file(target)
    if not target_skill.is_file() or _sha256(target_skill) != _sha256(source_skill):
        raise RuntimeError("installed ORIS routing skill differs from source")
    info = run(
        ["openclaw", "skills", "info", context.routing_skill_name, "--json"],
        cwd=context.repo_root,
        timeout=30,
    )
    if info.returncode != 0 or not _effective_skill_is_managed(context, info.stdout):
        raise RuntimeError("effective ORIS routing skill is overridden or unavailable")
    return {
        "name": context.routing_skill_name,
        "source_sha256": _sha256(source_skill),
        "installed_sha256": _sha256(target_skill),
        "effective_managed_source": True,
        "skill_content_recorded": False,
        "secret_values_recorded": False,
    }


def restore_routing_skill(backup: SkillBackup) -> None:
    target = backup.target_directory
    if target.exists() or target.is_symlink():
        if target.is_dir() and not target.is_symlink():
            shutil.rmtree(target)
        else:
            target.unlink()
    if backup.existed_before:
        shutil.copytree(backup.backup_directory, target, symlinks=True)
