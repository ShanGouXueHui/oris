from __future__ import annotations

import sys

from .context import discover_repo_root
from .engineering_scan import scan_repository_sources


def main() -> int:
    if sys.argv[1:] != ["--code-audit"]:
        return 64
    result = scan_repository_sources(discover_repo_root())
    print("===== SUMMARY =====")
    print("RESULT=" + ("CODE_AUDIT_PASS" if result["ok"] else "CODE_AUDIT_FAIL"))
    print(f"FILES_SCANNED={result['files_scanned']}")
    print(f"DUPLICATE_BINDINGS={len(result['duplicate_bindings'])}")
    print(f"AUTHORITY_VIOLATIONS={len(result['authority_violations'])}")
    print(f"DUPLICATE_FUNCTION_BODIES={len(result['duplicate_function_bodies'])}")
    print(f"IMPORT_CYCLES={len(result['import_cycles'])}")
    print(f"OVERSIZED_MODULES={len(result['oversized_modules'])}")
    print(f"FORBIDDEN_HARDCODING={len(result['forbidden_hardcoding'])}")
    print(f"LEGACY_PATH_FINDINGS={len(result['legacy_path_findings'])}")
    print("CONTRACT_ERROR=" + str(result["contract_error"] or ""))
    print("OPENCLAW_ACCESSED=NO")
    print("GATEWAY_RESTARTED=NO")
    print("TASK_SUBMITTED=NO")
    print("===== END SUMMARY =====")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
