from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINTS = (
    ROOT / "scripts" / "oris_free_mesh_api.py",
    ROOT / "scripts" / "oris_infer.py",
    ROOT / "scripts" / "runtime_execute.py",
)


def _load_from_external_working_directory(path: Path) -> subprocess.CompletedProcess[str]:
    code = (
        "import runpy; "
        f"runpy.run_path({str(path)!r}, run_name='oris_bootstrap_test')"
    )
    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    with tempfile.TemporaryDirectory() as directory:
        return subprocess.run(
            [sys.executable, "-I", "-c", code],
            cwd=directory,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )


def test_direct_entrypoints_bootstrap_repository_package() -> None:
    failures: list[str] = []
    for path in ENTRYPOINTS:
        result = _load_from_external_working_directory(path)
        if result.returncode != 0:
            failures.append(
                f"{path.name}: rc={result.returncode}, stderr={result.stderr[-500:]}"
            )
    assert not failures, "\n".join(failures)


def run_all() -> None:
    test_direct_entrypoints_bootstrap_repository_package()


if __name__ == "__main__":
    run_all()
