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
