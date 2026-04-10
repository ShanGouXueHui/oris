#!/usr/bin/env python3
import argparse
import json
import subprocess
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]

def slugify(name: str) -> str:
    return (name or "").strip().lower().replace(" ", "-") or "company"

def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def latest_bundle_for(company_name: str):
    slug = slugify(company_name)
    base = ROOT / "outputs" / "report_build" / f"company-profile-{slug}"
    paths = sorted(base.glob("**/company_profile_bundle.json"))
    return paths[-1] if paths else None

def run_cmd(cmd):
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return {
        "returncode": r.returncode,
        "stdout": r.stdout,
        "stderr": r.stderr,
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-json-path", required=True)
    ap.add_argument("--company-name", required=True)
    ap.add_argument("--focus-profile", default="")
    args = ap.parse_args()

    input_json_path = str(Path(args.input_json_path))
    company_name = args.company_name.strip()
    focus_profile = args.focus_profile.strip()

    before = latest_bundle_for(company_name)

    bundle_cmd = [
        "python3",
        "skills/report_build_skill/company_profile_bundle_runner.py",
        "--input-json-path", input_json_path,
        "--company-name", company_name,
    ]
    if focus_profile:
        bundle_cmd += ["--focus-profile", focus_profile]

    bundle_run = run_cmd(bundle_cmd)
    if bundle_run["returncode"] != 0:
        print(json.dumps({
            "ok": False,
            "stage": "bundle_runner",
            "returncode": bundle_run["returncode"],
            "stderr": bundle_run["stderr"][-4000:],
            "stdout": bundle_run["stdout"][-2000:]
        }, ensure_ascii=False, indent=2))
        raise SystemExit(1)

    after = latest_bundle_for(company_name)
    if not after:
        print(json.dumps({
            "ok": False,
            "stage": "locate_bundle",
            "message": "bundle not found after runner execution"
        }, ensure_ascii=False, indent=2))
        raise SystemExit(1)

    if before and after.resolve() == before.resolve():
        # allow same latest path only if it exists; still proceed
        pass

    polish_cmd = [
        "python3",
        "scripts/polish_company_profile_bundle.py",
        "--bundle-json-path", str(after)
    ]
    polish_run = run_cmd(polish_cmd)
    if polish_run["returncode"] != 0:
        print(json.dumps({
            "ok": False,
            "stage": "polish_bundle",
            "bundle_json_path": str(after.relative_to(ROOT)),
            "returncode": polish_run["returncode"],
            "stderr": polish_run["stderr"][-4000:],
            "stdout": polish_run["stdout"][-2000:]
        }, ensure_ascii=False, indent=2))
        raise SystemExit(1)

    polish_obj = {}
    try:
        polish_obj = json.loads(polish_run["stdout"])
    except Exception:
        polish_obj = {
            "raw_stdout": polish_run["stdout"][-4000:]
        }

    print(json.dumps({
        "ok": True,
        "ts": datetime.utcnow().isoformat() + "Z",
        "company_name": company_name,
        "focus_profile": focus_profile,
        "input_json_path": input_json_path,
        "bundle_json_path": str(after.relative_to(ROOT)),
        "polish_result": polish_obj
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
