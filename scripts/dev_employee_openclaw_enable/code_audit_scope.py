from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


DEFAULT_SCOPE_PATH = Path("config/dev_employee/code_audit_scope.json")


@dataclass(frozen=True)
class CodeAuditScope:
    directory_roots: tuple[Path, ...]
    files: tuple[Path, ...]
    architecture_directory_roots: tuple[Path, ...]
    architecture_files: tuple[Path, ...]


def _safe_relative(value: object, field: str) -> Path:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field} contains an empty path")
    path = Path(text)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"{field} must contain repository-relative paths")
    return path


def _paths(values: object, field: str) -> tuple[Path, ...]:
    if not isinstance(values, list):
        raise ValueError(f"{field} must be a list")
    result = tuple(_safe_relative(item, field) for item in values)
    if len(set(result)) != len(result):
        raise ValueError(f"{field} contains duplicate paths")
    return result


def _require_existing(repo_root: Path, paths: Iterable[Path], *, directories: bool) -> None:
    for relative in paths:
        target = repo_root / relative
        valid = target.is_dir() if directories else target.is_file()
        if not valid:
            kind = "directory" if directories else "file"
            raise ValueError(f"audit scope {kind} is missing: {relative.as_posix()}")


def load_code_audit_scope(
    repo_root: Path,
    relative_path: Path = DEFAULT_SCOPE_PATH,
) -> CodeAuditScope:
    payload = json.loads((repo_root / relative_path).read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise ValueError("unsupported code audit scope schema_version")
    scope = CodeAuditScope(
        directory_roots=_paths(payload.get("directory_roots"), "directory_roots"),
        files=_paths(payload.get("files"), "files"),
        architecture_directory_roots=_paths(
            payload.get("architecture_directory_roots"),
            "architecture_directory_roots",
        ),
        architecture_files=_paths(
            payload.get("architecture_files"),
            "architecture_files",
        ),
    )
    _require_existing(repo_root, scope.directory_roots, directories=True)
    _require_existing(repo_root, scope.files, directories=False)
    _require_existing(repo_root, scope.architecture_directory_roots, directories=True)
    _require_existing(repo_root, scope.architecture_files, directories=False)
    return scope


def source_paths(
    repo_root: Path,
    scope: CodeAuditScope,
    suffixes: set[str],
) -> tuple[Path, ...]:
    paths = {
        path.relative_to(repo_root)
        for relative_root in scope.directory_roots
        for path in (repo_root / relative_root).rglob("*")
        if path.is_file() and path.suffix.lower() in suffixes
    }
    paths.update(
        relative
        for relative in scope.files
        if (repo_root / relative).suffix.lower() in suffixes
    )
    return tuple(sorted(paths))


def architecture_paths(repo_root: Path, scope: CodeAuditScope) -> tuple[Path, ...]:
    paths = {
        path
        for relative_root in scope.architecture_directory_roots
        for path in (repo_root / relative_root).rglob("*.py")
        if path.is_file() and "__pycache__" not in path.parts
    }
    paths.update(repo_root / relative for relative in scope.architecture_files)
    return tuple(sorted(paths))
