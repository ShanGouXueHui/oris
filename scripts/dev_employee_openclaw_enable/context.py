from __future__ import annotations

import json
from pathlib import Path

from .models import EvidenceTarget, RuntimeContext
from .task_contract import load_json_object, load_runtime_contract, load_task_id


TASK_PATH = Path("memory/dev_employee/current_task.json")
REGISTRY_PATH = Path("orchestration/project_registry.json")
ACCEPTANCE_PATH = Path("config/dev_employee/openclaw_readonly_acceptance.json")


def discover_repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _latest_ready_evidence(directory: Path) -> Path:
    for path in sorted(directory.glob("*.json"), reverse=True):
        try:
            if load_json_object(path).get("result") == "READY":
                return path
        except Exception:
            continue
    raise RuntimeError("no READY read-only readiness evidence found")


def _validate_skill(path: Path, name: str, tools: tuple[str, ...]) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        raise RuntimeError("routing skill frontmatter is missing")
    try:
        closing = next(
            i for i, line in enumerate(lines[1:], 1) if line.strip() == "---"
        )
    except StopIteration as exc:
        raise RuntimeError("routing skill frontmatter is not closed") from exc
    metadata: dict[str, str] = {}
    for line in lines[1:closing]:
        if ":" in line:
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip().strip("\"'")
    if metadata.get("name") != name or not metadata.get("description"):
        raise RuntimeError("routing skill identity is invalid")
    if metadata.get("user-invocable", "").lower() != "false":
        raise RuntimeError("routing skill must not expose a user command")
    if metadata.get("disable-model-invocation", "false").lower() == "true":
        raise RuntimeError("routing skill must remain visible to the model")
    try:
        openclaw = json.loads(metadata.get("metadata", "{}")).get("openclaw")
    except (json.JSONDecodeError, AttributeError) as exc:
        raise RuntimeError("routing skill OpenClaw metadata is invalid") from exc
    if not isinstance(openclaw, dict) or openclaw.get("always") is not True:
        raise RuntimeError("routing skill must be always included")
    body = "\n".join(lines[closing + 1 :])
    if not set(tools).issubset(set(body.replace("`", "").split())):
        raise RuntimeError("routing skill does not name every approved tool")
    if "Never use `exec`" not in body:
        raise RuntimeError("routing skill does not forbid exec fallback")


def _evidence_target(root: Path, value: dict[str, str]) -> EvidenceTarget:
    return EvidenceTarget(
        directory=root / value["directory"],
        filename_prefix=value["filename_prefix"],
        commit_message_prefix=value["commit_message_prefix"],
    )


def load_context() -> RuntimeContext:
    root = discover_repo_root()
    task_id = load_task_id(root / TASK_PATH)
    acceptance_path = root / ACCEPTANCE_PATH
    raw = load_json_object(acceptance_path)
    contract = load_runtime_contract(acceptance_path)
    projects = load_json_object(root / REGISTRY_PATH).get("projects")
    if not isinstance(projects, dict):
        raise RuntimeError("project registry has no projects map")
    baseline = contract["baseline"]
    product = projects.get(baseline["project_key"])
    if not isinstance(product, dict) or not isinstance(product.get("local_path"), str):
        raise RuntimeError("baseline project is missing from project registry")

    runtime = contract["runtime"]
    plugin = contract["plugin"]
    routes = contract["routes"]
    skill = contract["skill"]
    tools = contract["tools"]
    agent = contract["agent"]
    evidence = contract["evidence_targets"]
    skill_source = (root / skill["source_directory"]).resolve()
    if root not in skill_source.parents:
        raise RuntimeError("routing skill source escapes the ORIS repository")
    _validate_skill(
        skill_source / "SKILL.md",
        skill["name"],
        contract["approved_tools"],
    )
    readiness = root / raw["readiness_evidence_directory"]

    return RuntimeContext(
        repo_root=root,
        task_id=task_id,
        product_repo=Path(product["local_path"]).expanduser(),
        expected_product_commit=contract["expected_commit"],
        openclaw_config=Path(runtime["openclaw_config_path"]).expanduser(),
        backup_root=Path(runtime["backup_root"]).expanduser(),
        managed_skills_root=Path(runtime["managed_skills_root"]).expanduser(),
        routing_skill_name=skill["name"],
        routing_skill_source=skill_source,
        routing_skill_force_replace=skill["force_replace"],
        gateway_service=runtime["gateway_service"],
        gateway_url=contract["gateway_url"],
        public_url=contract["public_url"],
        public_root_route=routes["root"],
        restricted_routes=tuple(routes["restricted"]),
        plugin_id=plugin["id"],
        plugin_version=plugin["version"],
        approved_tools=contract["approved_tools"],
        required_hooks=contract["required_hooks"],
        marker_file=Path(plugin["private_marker"]).expanduser(),
        internal_ports=contract["internal_ports"],
        required_profile=contract["required_profile"],
        profile_expansion=contract["profile_expansion"],
        safe_probe_candidates=tuple(tools["safe_builtin_probe_candidates"]),
        direct_probe_session_key=tools["direct_probe_session_key"],
        session_prefix=agent["session_prefix"],
        require_gateway_transport=agent["require_gateway_transport"],
        require_persisted_native_session=agent["require_persisted_native_session"],
        acceptance_turns=contract["turns"],
        turn_timeout_seconds=agent["turn_timeout_seconds"],
        telemetry_wait_seconds=agent["telemetry_wait_seconds"],
        telemetry_path=Path(plugin["telemetry_path"]).expanduser(),
        enablement_evidence=_evidence_target(root, evidence["enablement"]),
        effective_surface_evidence=_evidence_target(
            root,
            evidence["effective_surface_diagnostic"],
        ),
        readiness_evidence=_latest_ready_evidence(readiness),
    )
