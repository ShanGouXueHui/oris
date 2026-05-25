# ORIS Dev Employee Supervised Bridge v2.1 Retrospective — 2026-05-25

## Result

Supervised bridge v2.1 completed the formal Pydantic cleanup task end-to-end.

- Task id: `formal-test-pydantic-cleanup-v2-20260525`
- Product repository: `ShanGouXueHui/oris-final-acceptance-api`
- Product commit SHA: `bf9853d2bdf80dad4278021e03f877932ee31d4a`
- Product remote SHA: `bf9853d2bdf80dad4278021e03f877932ee31d4a`
- ORIS evidence commit SHA: `7e8c1d17eeb6778f0348445a78afd2d7c44919ec`
- ORIS remote SHA: `7e8c1d17eeb6778f0348445a78afd2d7c44919ec`

## What was validated

The bridge now validates the complete execution loop:

```text
queued task descriptor
  -> host bridge claim
  -> Codex CLI local execution
  -> Codex structured result
  -> host-side final checks
  -> product commit/push
  -> product remote verification
  -> ORIS evidence commit/push
  -> ORIS remote verification
```

## Evidence

Host-side checks passed:

- `/home/admin/projects/oris-final-acceptance-api/.venv/bin/python -m py_compile app/main.py`
- `/home/admin/projects/oris-final-acceptance-api/.venv/bin/python -m pytest -q`
- `/home/admin/projects/oris-final-acceptance-api/.venv/bin/python -m pytest -q -W error::DeprecationWarning`

Both pytest evidence files recorded:

```text
........                                                                 [100%]
8 passed in 0.27s
```

## Defect found and fixed

The original v2 bridge used a bare `python` command in the host-side final check. On the Ubuntu host, `python` was not available, causing:

```text
FileNotFoundError: [Errno 2] No such file or directory: 'python'
```

The v2.1 wrapper fixed this by selecting:

1. product `.venv/bin/python` if present;
2. otherwise `python3`.

## Follow-up improvements

Promote v2.1 behavior into the primary bridge implementation and add:

1. no bare `python` dependency;
2. structured failure handling instead of uncaught traceback;
3. stale running-task recovery;
4. commit Codex result/log evidence when safe;
5. mark `oris_evidence_pending=false` after ORIS evidence push succeeds;
6. one command for `--once` and `--recover-stale`.
