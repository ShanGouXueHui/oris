from __future__ import annotations

import ast
import hashlib
from collections import defaultdict
from pathlib import Path
from typing import Any


_PACKAGE_ROOTS = (
    Path("scripts/dev_employee_openclaw_enable"),
    Path("scripts/dev_employee_quality"),
)
_CALL_CHAIN_FILES = (
    Path("scripts/oris_free_mesh_api.py"),
    Path("scripts/oris_infer.py"),
    Path("scripts/runtime_execute.py"),
    Path("oris_vnext/free_mesh_compat.py"),
    Path("oris_vnext/free_mesh_http.py"),
    Path("oris_vnext/free_mesh_inference.py"),
    Path("oris_vnext/infer_refresh.py"),
    Path("oris_vnext/openai_chat_contract.py"),
    Path("oris_vnext/runtime_execution_engine.py"),
    Path("oris_vnext/runtime_execution_state.py"),
    Path("oris_vnext/runtime_provider_client.py"),
    Path("tests/test_free_mesh_tool_calling.py"),
    Path("tests/test_free_mesh_protocol.py"),
    Path("tests/test_script_entrypoint_bootstrap.py"),
)


def _module_name(repo_root: Path, path: Path) -> str:
    return path.relative_to(repo_root).with_suffix("").as_posix().replace("/", ".")


def target_python_files(repo_root: Path) -> tuple[Path, ...]:
    files = {
        path
        for relative_root in _PACKAGE_ROOTS
        for path in (repo_root / relative_root).glob("*.py")
        if path.is_file()
    }
    files.update(
        repo_root / relative
        for relative in _CALL_CHAIN_FILES
        if (repo_root / relative).is_file()
    )
    return tuple(sorted(files))


def _function_digest(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str | None:
    if len(list(ast.walk(node))) < 12:
        return None
    normalized = ast.FunctionDef(
        name="function",
        args=node.args,
        body=node.body,
        decorator_list=[],
        returns=node.returns,
        type_comment=node.type_comment,
    )
    return hashlib.sha256(
        ast.dump(normalized, include_attributes=False).encode("utf-8")
    ).hexdigest()


def _resolve_import(current_module: str, node: ast.ImportFrom) -> set[str]:
    package = current_module.split(".")[:-1]
    if node.level:
        ascend = node.level - 1
        base = package[: len(package) - ascend] if ascend <= len(package) else []
        if node.module:
            return {".".join([*base, node.module])}
        return {".".join([*base, item.name]) for item in node.names}
    return {node.module} if node.module else set()


def _cycles(graph: dict[str, set[str]]) -> list[list[str]]:
    found: set[tuple[str, ...]] = set()

    def visit(node: str, path: list[str]) -> None:
        for child in graph.get(node, set()):
            if child not in graph:
                continue
            if child in path:
                core = path[path.index(child) :]
                rotations = [
                    tuple(core[index:] + core[:index])
                    for index in range(len(core))
                ]
                found.add(min(rotations))
            elif len(path) <= len(graph):
                visit(child, [*path, child])

    for node in graph:
        visit(node, [node])
    return [list(item) for item in sorted(found)]


def scan_python_architecture(
    repo_root: Path,
    authorities: dict[str, str],
) -> dict[str, Any]:
    files = target_python_files(repo_root)
    module_by_path = {path: _module_name(repo_root, path) for path in files}
    known_modules = set(module_by_path.values())
    definitions: dict[str, list[str]] = defaultdict(list)
    bodies: dict[str, list[tuple[str, str]]] = defaultdict(list)
    graph: dict[str, set[str]] = {}

    for path, module in module_by_path.items():
        relative = path.relative_to(repo_root).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imports: set[str] = set()
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                definitions[node.name].append(relative)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                digest = _function_digest(node)
                if digest:
                    bodies[digest].append((relative, node.name))
            if isinstance(node, ast.Import):
                imports.update(item.name for item in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.update(_resolve_import(module, node))
        graph[module] = {
            candidate
            for imported in imports
            for candidate in known_modules
            if candidate == imported or candidate.startswith(imported + ".")
        } - {module}

    authority_violations = {
        name: {"expected": expected, "actual": definitions.get(name, [])}
        for name, expected in authorities.items()
        if definitions.get(name, []) != [expected]
    }
    duplicate_bodies = [
        [
            {"file": file_name, "function": function_name}
            for file_name, function_name in rows
        ]
        for rows in bodies.values()
        if len(rows) > 1
    ]
    return {
        "files_scanned": len(files),
        "authority_violations": authority_violations,
        "duplicate_function_bodies": duplicate_bodies,
        "import_cycles": _cycles(graph),
    }
