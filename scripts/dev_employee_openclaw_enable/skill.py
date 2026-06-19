from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import RuntimeContext
from .process import run
from .state import load_json


@dataclass(frozen=True)
class SkillPathBackup:
    target: Path
    backup: Path
    existed_before: bool
    authoritative_source: bool


@dataclass(frozen=True)
class SkillBackup:
    paths: tuple[SkillPathBackup, ...]


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


def _workspace_paths(context: RuntimeContext) -> tuple[Path, ...]:
    config = load_json(context.openclaw_config)
    agents = config.get("agents") if isinstance(config.get("agents"), dict) else {}
    workspaces: set[Path] = {Path.home() / ".openclaw" / "workspace"}

    def add_workspace(value: Any) -> None:
        if isinstance(value, str) and value.strip():
            workspaces.add(Path(value).expanduser().resolve())

    defaults = agents.get("defaults") if isinstance(agents.get("defaults"), dict) else {}
    add_workspace(defaults.get("workspace"))
    listed = agents.get("list") if isinstance(agents.get("list"), list) else []
    for item in listed:
        if isinstance(item, dict):
            add_workspace(item.get("workspace"))
    for key, item in agents.items():
        if key in {"defaults", "list"} or not isinstance(item, dict):
            continue
        add_workspace(item.get("workspace"))
    return tuple(
        sorted((path / "skills" / context.routing_skill_name).resolve() for path in workspaces)
    )


def validate_skill_cli() -> bool:
    install_help = run(["openclaw", "skills", "install", "--help"], timeout=30)
    info_help = run(["openclaw", "skills", "info", "--help"], timeout=30)
    if install_help.returncode != 0 or info_help.returncode != 0:
        return False
    install_text = install_help.stdout + "\n" + install_help.stderr
    info_text = info_help.stdout + "\n" + info_help.stderr
    return all(flag in install_text for flag in ("--as", "--global", "--force")) and "--json" in info_text


def backup_routing_skill(
    context: RuntimeContext,
    transaction_backup_directory: Path,
) -> SkillBackup:
    source = context.routing_skill_source.resolve()
    targets = {_managed_target(context), *_workspace_paths(context)}
    backups: list[SkillPathBackup] = []
    for index, target in enumerate(sorted(targets)):
        if target.is_symlink():
            raise RuntimeError("routing skill target must not be a symlink")
        existed = target.exists()
        backup = transaction_backup_directory / "routing-skills-before" / str(index)
        if existed:
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(target, backup, symlinks=True)
        backups.append(
            SkillPathBackup(
                target=target,
                backup=backup,
                existed_before=existed,
                authoritative_source=target == source,
            )
        )
    return SkillBackup(tuple(backups))


def _remove_path(path: Path) -> None:
    if not path.exists() and not path.is_symlink():
        return
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()


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


def _effective_skill_is_approved(context: RuntimeContext, info_output: str) -> bool:
    payload = _parse_json_output(info_output)
    if payload is None:
        return False
    managed = _managed_target(context)
    source = context.routing_skill_source.resolve()
    approved = {
        str(managed),
        str(_skill_file(managed)),
        str(source),
        str(_skill_file(source)),
    }
    for value in _find_path_strings(payload):
        try:
            resolved = str(Path(value).expanduser().resolve())
        except Exception:
            continue
        if resolved in approved:
            return True
    return False


def install_routing_skill(
    context: RuntimeContext,
    backup: SkillBackup,
) -> dict[str, Any]:
    managed = _managed_target(context)
    removed_shadow_count = 0
    for item in backup.paths:
        if item.authoritative_source or item.target == managed:
            continue
        if item.target.exists():
            _remove_path(item.target)
            removed_shadow_count += 1

    source_skill = _skill_file(context.routing_skill_source)
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

    target_skill = _skill_file(managed)
    if not target_skill.is_file() or _sha256(target_skill) != _sha256(source_skill):
        raise RuntimeError("installed ORIS routing skill differs from source")
    info = run(
        ["openclaw", "skills", "info", context.routing_skill_name, "--json"],
        cwd=context.repo_root,
        timeout=30,
    )
    if info.returncode != 0 or not _effective_skill_is_approved(context, info.stdout):
        raise RuntimeError("effective ORIS routing skill is overridden or unavailable")
    return {
        "name": context.routing_skill_name,
        "source_sha256": _sha256(source_skill),
        "installed_sha256": _sha256(target_skill),
        "effective_source_approved": True,
        "removed_shadow_count": removed_shadow_count,
        "skill_content_recorded": False,
        "secret_values_recorded": False,
    }


def restore_routing_skill(backup: SkillBackup) -> None:
    for item in backup.paths:
        _remove_path(item.target)
        if item.existed_before:
            item.target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(item.backup, item.target, symlinks=True)
