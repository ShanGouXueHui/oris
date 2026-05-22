#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROJECTS_ROOT = Path('/home/admin/projects').resolve()
OUT_JSON = ROOT / 'logs' / 'dev_employee' / 'latest_project_venv_install.json'
OUT_MD = ROOT / 'logs' / 'dev_employee' / 'latest_project_venv_install.md'


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(cmd: list[str], cwd: Path | None = None, timeout: int = 300) -> dict[str, Any]:
    try:
        p = subprocess.run(cmd, cwd=str(cwd) if cwd else None, text=True, capture_output=True, timeout=timeout)
        return {
            'rc': p.returncode,
            'stdout': (p.stdout or '')[-12000:],
            'stderr': (p.stderr or '')[-8000:],
            'cmd': cmd,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            'rc': 124,
            'stdout': str(exc.stdout or '')[-12000:],
            'stderr': str(exc.stderr or '')[-8000:],
            'cmd': cmd,
            'timeout': True,
        }


def safe_project_path(raw: str) -> Path:
    p = Path(raw).expanduser().resolve()
    if p == ROOT.resolve():
        raise SystemExit('refuse to install project dependencies into ORIS platform repo')
    if PROJECTS_ROOT not in p.parents:
        raise SystemExit(f'target path must be under {PROJECTS_ROOT}: {p}')
    return p


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--target-path', required=True)
    parser.add_argument('--requirements', default='requirements.txt')
    parser.add_argument('--run-pytest', action='store_true')
    args = parser.parse_args()

    target = safe_project_path(args.target_path)
    requirements = target / args.requirements
    venv = target / '.venv'
    python = venv / 'bin' / 'python'
    pip = venv / 'bin' / 'pip'

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)

    steps: list[dict[str, Any]] = []
    ok = True
    reason = ''

    if not target.exists():
        ok = False
        reason = 'target_path_not_found'
    elif not requirements.exists():
        ok = False
        reason = 'requirements_not_found'
    else:
        steps.append(run(['python3', '-m', 'venv', str(venv)], cwd=target, timeout=120))
        if steps[-1]['rc'] != 0:
            ok = False
            reason = 'venv_create_failed'
        else:
            steps.append(run([str(pip), 'install', '--upgrade', 'pip'], cwd=target, timeout=300))
            if steps[-1]['rc'] != 0:
                ok = False
                reason = 'pip_upgrade_failed'
            else:
                steps.append(run([str(pip), 'install', '-r', str(requirements)], cwd=target, timeout=600))
                if steps[-1]['rc'] != 0:
                    ok = False
                    reason = 'requirements_install_failed'

    pytest_result = None
    if ok and args.run_pytest:
        pytest_result = run([str(python), '-m', 'pytest', '-q'], cwd=target, timeout=300)
        steps.append(pytest_result)
        if pytest_result['rc'] != 0:
            ok = False
            reason = 'pytest_failed'

    payload = {
        'ok': ok,
        'generated_at': utc_now(),
        'mode': 'project_venv_only',
        'target_path': str(target),
        'requirements': str(requirements),
        'venv_path': str(venv),
        'reason': reason,
        'steps': steps,
        'pytest_result': pytest_result,
        'forbidden_actions': ['apt install', 'system package changes', 'systemd changes', 'nginx changes', 'secret writes'],
    }

    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    OUT_MD.write_text(
        '# Project Venv Install\n\n'
        f"- ok: `{ok}`\n"
        f"- generated_at: `{payload['generated_at']}`\n"
        f"- mode: `project_venv_only`\n"
        f"- target_path: `{target}`\n"
        f"- requirements: `{requirements}`\n"
        f"- venv_path: `{venv}`\n"
        f"- reason: `{reason}`\n"
        f"- run_pytest: `{bool(args.run_pytest)}`\n",
        encoding='utf-8',
    )
    print(json.dumps({'ok': ok, 'json_out': str(OUT_JSON), 'md_out': str(OUT_MD), 'reason': reason}, ensure_ascii=False))
    return 0 if ok else 2


if __name__ == '__main__':
    raise SystemExit(main())
