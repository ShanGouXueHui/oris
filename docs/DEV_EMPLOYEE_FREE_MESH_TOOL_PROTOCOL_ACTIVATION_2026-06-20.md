# Dev Employee Free Mesh Tool Protocol Activation — 2026-06-20

## Purpose

Activate the audited Free Mesh tool-calling implementation on the development machine and immediately run the existing controlled model/tool diagnostic.

## Single entrypoint

```bash
bash scripts/dev_employee_activate_free_mesh_tool_calling_and_diagnose.sh
```

The entrypoint performs the following ordered transaction:

1. run the exact repository code-first audit;
2. stop immediately without runtime access if the code gate fails;
3. restart only `oris-free-mesh-api.service`;
4. read the endpoint from `config/oris_free_mesh_api.json`;
5. require the endpoint to remain loopback-only;
6. poll `/v1/health` until the service reports:
   - `ok=true`;
   - `service=oris-free-mesh-api`;
   - `protocol_version=2`;
   - `tool_calling=true`;
7. invoke the existing model/tool diagnostic;
8. rely on the existing exact policy rollback and final queue/product/listener invariants;
9. publish sanitized GitHub evidence;
10. print the standard summary only.

## 2026-06-20 bootstrap regression

The first activation attempt returned:

- service state `activating`;
- no protocol version;
- no tool-calling readiness;
- no OpenClaw access;
- no Gateway restart;
- no product task submission.

The failure was traced to a direct-entrypoint import regression introduced during the Free Mesh protocol refactor. The previous service entrypoint inserted the repository root into `sys.path` before importing `oris_vnext`. The refactored files imported `oris_vnext` first and calculated the repository root afterwards.

This breaks when systemd or a subprocess executes an absolute script path because Python places the script directory, not the repository root, on the initial module search path. The affected entrypoints were:

- `scripts/oris_free_mesh_api.py`;
- `scripts/oris_infer.py`;
- `scripts/runtime_execute.py`.

All three now restore the repository bootstrap before package imports. `tests/test_script_entrypoint_bootstrap.py` reproduces the systemd-style environment by clearing `PYTHONPATH`, changing to an external working directory, enabling Python isolated mode, and loading each entrypoint by absolute path.

## Failure behavior

### Code gate failure

- Free Mesh is not restarted.
- OpenClaw is not accessed.
- Gateway is not restarted.
- No product task is submitted.

### Free Mesh restart or protocol failure

- OpenClaw is not accessed.
- Gateway is not restarted.
- No product task is submitted.
- The summary directs investigation to the Free Mesh service journal.
- The model diagnostic CLI records protocol readiness in evidence when it reaches the protocol gate.

### Diagnostic failure after protocol readiness

The existing model/tool diagnostic owns rollback and evidence publication. It restores the exact tools-denied baseline and verifies queue, product repository, and loopback listener invariants.

## Security and privacy

- No OpenClaw reinstall or upgrade.
- No write tools.
- No product task submission.
- No prompt, conversation content, tool schema, tool arguments, tool results, endpoint URL, or authentication value is recorded in the protocol evidence.
- Only service state, loopback assertion, port, HTTP status, protocol version, tool-calling boolean, attempt count, and error type are retained.

## Acceptance progression

- Generic built-in tool and ORIS queue tool both call successfully: proceed to the full three-tool natural-language acceptance.
- Built-in succeeds but ORIS tool fails: inspect Agent Harness / Skill routing.
- No tool call occurs although protocol v2 is confirmed: inspect the selected downstream provider/model capability and its response.
