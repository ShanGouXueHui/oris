from __future__ import annotations

from pathlib import PurePosixPath


def _within(path: PurePosixPath, prefix: PurePosixPath) -> bool:
    return path == prefix or prefix in path.parents


def authorize_relative_path(
    value: str,
    *,
    allowed_scopes: tuple[str, ...],
    forbidden_scopes: tuple[str, ...],
) -> PurePosixPath:
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("repository-relative path required")
    if any(_within(path, PurePosixPath(item)) for item in forbidden_scopes):
        raise PermissionError("path is within forbidden scope")
    if allowed_scopes and not any(
        _within(path, PurePosixPath(item)) for item in allowed_scopes
    ):
        raise PermissionError("path is outside allowed scope")
    return path
