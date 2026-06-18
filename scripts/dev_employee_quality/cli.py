from __future__ import annotations

import sys
from pathlib import Path

from .report import write_report


def main() -> int:
    if len(sys.argv) < 2:
        print("repository root argument is required")
        return 64
    repo_root = Path(sys.argv[1]).expanduser().resolve()
    output = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    report, target = write_report(repo_root, output)
    print("===== SUMMARY =====")
    print("RESULT=" + str(report["result"]))
    print("FILES_SCANNED=" + str(report["files_scanned"]))
    print("FINDING_COUNT=" + str(report["finding_count"]))
    print("REPORT=" + str(target.relative_to(repo_root)))
    print("FILES_MODIFIED=NO")
    print("NEXT_ACTION=" + ("FIX_ALL_REPORTED_FINDINGS" if report["finding_count"] else "QUALITY_GATE_READY"))
    print("SEND_TO_CHAT=THIS_SUMMARY_ONLY")
    print("===== END SUMMARY =====")
    return 0 if report["finding_count"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
