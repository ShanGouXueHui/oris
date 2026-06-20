from __future__ import annotations

from pathlib import Path


def discover_repo_root(anchor: Path | None = None) -> Path:
    current = (anchor or Path(__file__)).resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists() or (
            (candidate / "orchestration/project_registry.json").is_file()
            and (candidate / "scripts").is_dir()
        ):
            return candidate
    raise RuntimeError("ORIS repository root not found")
