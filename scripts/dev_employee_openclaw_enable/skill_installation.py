from __future__ import annotations

import hashlib
import os
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import RuntimeContext
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
    root = context.managed_skills_root.expanduser().resolve()
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


def validate_skill_install_target(context: RuntimeContext) -> bool:
    source_skill = _skill_file(context.routing_skill_source)
    if not source_skill.is_file():
        return False
    root = context.managed_skills_root.expanduser().resolve()
    home = Path.home().resolve()
    if root != home and home not in root.parents:
        return False
    ancestor = root
    while not ancestor.exists() and ancestor != ancestor.parent:
        ancestor = ancestor.parent
    return ancestor.is_dir() and os.access(ancestor, os.W_OK | os.X_OK)


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


def _copy_skill_atomically(context: RuntimeContext) -> Path:
    source = context.routing_skill_source.resolve()
    source_skill = _skill_file(source)
    root = context.managed_skills_root.expanduser().resolve()
    target = _managed_target(context)
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(root, 0o700)
    temporary = root / f".{context.routing_skill_name}.tmp-{uuid.uuid4().hex}"
    try:
        shutil.copytree(source, temporary, symlinks=False)
        copied_skill = _skill_file(temporary)
        if not copied_skill.is_file() or _sha256(copied_skill) != _sha256(source_skill):
            raise RuntimeError("staged ORIS routing skill differs from source")
        _remove_path(target)
        os.replace(temporary, target)
    finally:
        _remove_path(temporary)
    return target


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

    target = _copy_skill_atomically(context)
    source_skill = _skill_file(context.routing_skill_source)
    target_skill = _skill_file(target)
    if not target_skill.is_file() or _sha256(target_skill) != _sha256(source_skill):
        raise RuntimeError("installed ORIS routing skill differs from source")
    remaining_shadows = [
        str(item.target)
        for item in backup.paths
        if not item.authoritative_source
        and item.target != managed
        and item.target.exists()
    ]
    if remaining_shadows:
        raise RuntimeError("a higher-priority ORIS routing skill shadow remains")
    return {
        "name": context.routing_skill_name,
        "installation_method": "managed_atomic_directory_copy",
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
