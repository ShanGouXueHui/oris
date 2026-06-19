from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

from .models import RuntimeContext


TASK_PATH = Path("memory/dev_employee/current_task.json")
REGISTRY_PATH = Path("orchestration/project_registry.json")
ACCEPTANCE_PATH = Path("config/dev_employee/openclaw_readonly_acceptance.json")


def _load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def discover_repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _latest_ready_evidence(evidence_directory: Path) -> Path:
    for path in sorted(evidence_directory.glob("*.json"), reverse=True):
        try:
            payload = _load_json(path)
        except Exception:
            continue
        if payload.get("result") == "READY":
            return path
    raise RuntimeError("no READY read-only readiness evidence found")


def _resolve_profile_expansion(acceptance: dict, task: dict) -> tuple[str, ...]:
    profile = str(acceptance["tool_policy"]["required_profile"])
    runtime_version = str(task["platform_state"]["openclaw_version"]).split()[0]
    version_rules = acceptance["tool_policy"]["profile_expansions"].get(runtime_version)
    if not isinstance(version_rules, dict):
        raise RuntimeError(f"no tool profile expansion for OpenClaw {runtime_version}")
    values = version_rules.get(profile)
    if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
        raise RuntimeError(f"invalid tool profile expansion for {profile}")
    return tuple(values)


def _skill_frontmatter(skill_file: Path) -> tuple[dict[str, str], str]:
    text = skill_file.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise RuntimeError("routing skill frontmatter is missing")
    try:
        closing = next(
            index
            for index, line in enumerate(lines[1:], 1)
            if line.strip() == "---"
        )
    except StopIteration as exc:
        raise RuntimeError("routing skill frontmatter is not closed") from exc
    metadata: dict[str, str] = {}
    for line in lines[1:closing]:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip('"\'')
    return metadata, "\n".join(lines[closing + 1 :])


def _validate_skill_metadata(metadata: dict[str, str]) -> None:
    if metadata.get("user-invocable", "").lower() != "false":
        raise RuntimeError("routing skill must not expose a user command")
    if metadata.get("disable-model-invocation", "false").lower() == "true":
        raise RuntimeError("routing skill must remain visible to the model")
    try:
        openclaw_metadata = json.loads(metadata.get("metadata", "{}"))
    except json.JSONDecodeError as exc:
        raise RuntimeError("routing skill OpenClaw metadata is invalid") from exc
    if not isinstance(openclaw_metadata, dict):
        raise RuntimeError("routing skill OpenClaw metadata is not an object")
    openclaw = openclaw_metadata.get("openclaw")
    if not isinstance(openclaw, dict) or openclaw.get("always") is not True:
        raise RuntimeError("routing skill must be always included in the agent prompt")


def _validate_routing_skill(
    skill_file: Path,
    configured_name: str,
    approved_tools: tuple[str, ...],
) -> None:
    metadata, body = _skill_frontmatter(skill_file)
    if metadata.get("name") != configured_name:
        raise RuntimeError("routing skill name differs from acceptance configuration")
    if not metadata.get("description"):
        raise RuntimeError("routing skill description is missing")
    _validate_skill_metadata(metadata)
    if not set(approved_tools).issubset(set(body.replace("`", "").split())):
        raise RuntimeError("routing skill does not name every approved typed tool")
    if "Never use `exec`" not in body:
        raise RuntimeError("routing skill does not forbid exec fallback")


def load_context() -> RuntimeContext:
    repo_root = discover_repo_root()
    task = _load_json(repo_root / TASK_PATH)
    registry = _load_json(repo_root / REGISTRY_PATH)
    acceptance = _load_json(repo_root / ACCEPTANCE_PATH)
    if acceptance.get("schema_version") != 2:
        raise RuntimeError("unsupported automatic acceptance configuration schema")

    projects = registry.get("projects")
    if not isinstance(projects, dict):
        raise RuntimeError("project registry has no projects map")
    product = projects.get(acceptance.get("baseline_project_key"))
    if not isinstance(product, dict):
        raise RuntimeError("baseline project is missing from project registry")

    architecture = task.get("architecture_decision")
    platform = task.get("platform_state")
    plugin = task.get("installed_plugin_state")
    if not all(isinstance(value, dict) for value in (architecture, platform, plugin)):
        raise RuntimeError(
            "current task is missing architecture, platform, or plugin state"
        )

    gateway_url = str(architecture["openclaw_local_gateway"]).rstrip("/")
    parsed_gateway = urlparse(gateway_url)
    if parsed_gateway.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise RuntimeError("OpenClaw gateway is not loopback-scoped")
    if parsed_gateway.port != int(platform["openclaw_gateway_port"]):
        raise RuntimeError("OpenClaw gateway URL and platform port disagree")

    approved_tools = tuple(plugin.get("runtime_tools") or ())
    required_hooks = tuple(plugin.get("runtime_hooks") or ())
    if len(approved_tools) != 3 or len(required_hooks) != 3:
        raise RuntimeError(
            "current task does not define the exact approved tool and hook sets"
        )

    agent_acceptance = acceptance["agent_acceptance"]
    turns = agent_acceptance["turns"]
    if not isinstance(turns, list) or len(turns) != len(approved_tools):
        raise RuntimeError("automatic acceptance turns do not match approved tool count")
    expected_turn_tools = {
        str(item.get("expected_tool")) for item in turns if isinstance(item, dict)
    }
    if expected_turn_tools != set(approved_tools):
        raise RuntimeError("automatic acceptance tool names do not match current task")

    routing_skill = acceptance["routing_skill"]
    if routing_skill.get("install_scope") != "global":
        raise RuntimeError("only managed global routing skill installation is supported")
    routing_skill_source = (
        repo_root / str(routing_skill["source_directory"])
    ).resolve()
    if repo_root not in routing_skill_source.parents:
        raise RuntimeError("routing skill source escapes the ORIS repository")
    skill_file = routing_skill_source / "SKILL.md"
    if not skill_file.is_file():
        raise RuntimeError("routing skill source is missing SKILL.md")
    _validate_routing_skill(
        skill_file,
        str(routing_skill["name"]),
        approved_tools,
    )

    telemetry_path = Path(
        str(plugin.get("telemetry_path") or acceptance["telemetry"]["default_path"])
    ).expanduser()
    marker_file = Path(str(plugin["private_marker"])).expanduser()
    openclaw_config = Path(str(acceptance["openclaw_config_path"])).expanduser()
    backup_root = Path(str(acceptance["backup_root"])).expanduser()
    managed_skills_root = Path(str(acceptance["managed_skills_root"])).expanduser()
    evidence_directory = repo_root / str(acceptance["evidence"]["directory"])
    readiness_directory = repo_root / str(acceptance["readiness_evidence_directory"])
    public_routes = acceptance["public_routes"]
    tool_policy = acceptance["tool_policy"]

    return RuntimeContext(
        repo_root=repo_root,
        task_id=str(task["task_id"]),
        product_repo=Path(str(product["local_path"])).expanduser(),
        expected_product_commit=str(platform["product_baseline_commit"]),
        openclaw_config=openclaw_config,
        backup_root=backup_root,
        managed_skills_root=managed_skills_root,
        routing_skill_name=str(routing_skill["name"]),
        routing_skill_source=routing_skill_source,
        routing_skill_force_replace=bool(routing_skill["force_replace"]),
        gateway_service=str(acceptance["gateway_service"]),
        gateway_url=gateway_url,
        public_url=str(architecture["primary_public_entry"]).rstrip("/"),
        public_root_route=str(public_routes["root"]),
        restricted_routes=tuple(str(item) for item in public_routes["restricted"]),
        plugin_id=str(plugin["plugin_id"]),
        plugin_version=str(plugin["version"]),
        approved_tools=approved_tools,
        required_hooks=required_hooks,
        marker_file=marker_file,
        internal_ports=(
            int(platform["enqueue_status_port"]),
            int(platform["intake_port"]),
        ),
        required_profile=str(tool_policy["required_profile"]),
        profile_expansion=_resolve_profile_expansion(acceptance, task),
        safe_probe_candidates=tuple(tool_policy["safe_builtin_probe_candidates"]),
        direct_probe_session_key=str(tool_policy["direct_probe_session_key"]),
        session_prefix=str(agent_acceptance["session_prefix"]),
        require_gateway_transport=bool(
            agent_acceptance["require_gateway_transport"]
        ),
        require_persisted_native_session=bool(
            agent_acceptance["require_persisted_native_session"]
        ),
        acceptance_turns=tuple(dict(item) for item in turns),
        turn_timeout_seconds=int(agent_acceptance["turn_timeout_seconds"]),
        telemetry_wait_seconds=int(agent_acceptance["telemetry_wait_seconds"]),
        telemetry_path=telemetry_path,
        evidence_directory=evidence_directory,
        evidence_commit_prefix=str(acceptance["evidence"]["commit_message_prefix"]),
        readiness_evidence=_latest_ready_evidence(readiness_directory),
    )
