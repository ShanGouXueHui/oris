from __future__ import annotations

import ast
import json
from collections import defaultdict

from .models import Finding, SourceFile


SCRIPT_SUFFIXES = {".ts", ".tsx", ".js", ".mjs", ".cjs"}


def _findings(path: str, scope: str, rows: list[tuple[str, int]]) -> list[Finding]:
    grouped: dict[str, list[int]] = defaultdict(list)
    for name, line in rows:
        grouped[name].append(line)
    return [
        Finding(
            "duplicate_symbol",
            path,
            lines[1],
            f"{scope} symbol {name} is defined more than once",
            ",".join(map(str, lines)),
        )
        for name, lines in sorted(grouped.items())
        if len(lines) > 1
    ]


def _targets(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Name):
        return [node.id]
    if isinstance(node, (ast.Tuple, ast.List)):
        return [item.id for item in node.elts if isinstance(item, ast.Name)]
    return []


def _bindings(body: list[ast.stmt]) -> list[tuple[str, int]]:
    rows: list[tuple[str, int]] = []
    for node in body:
        names: list[str] = []
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names = [node.name]
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [item.asname or item.name.split(".")[0] for item in node.names]
        elif isinstance(node, ast.Assign):
            names = [name for target in node.targets for name in _targets(target)]
        elif isinstance(node, ast.AnnAssign):
            names = _targets(node.target)
        rows.extend((name, getattr(node, "lineno", 1)) for name in names)
    return rows


def scan_python(source: SourceFile) -> list[Finding]:
    try:
        tree = ast.parse(source.text, filename=source.relative_path)
        compile(source.text, source.relative_path, "exec")
    except SyntaxError as exc:
        return [Finding("python_syntax", source.relative_path, exc.lineno or 1, str(exc))]
    result = _findings(source.relative_path, "module", _bindings(tree.body))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            result.extend(
                _findings(source.relative_path, f"class {node.name}", _bindings(node.body))
            )
    return result


def _shell_name(line: str) -> str | None:
    stripped = line.strip()
    if line != line.lstrip():
        return None
    if stripped.startswith("function ") and stripped.endswith("{"):
        return stripped[9:].split("(", 1)[0].strip()
    return stripped.split("(", 1)[0].strip() if stripped.endswith("() {") else None


def _script_name(line: str) -> str | None:
    if line != line.lstrip():
        return None
    stripped = line.strip().removeprefix("export ").removeprefix("default ")
    for prefix in ("async function ", "function ", "class ", "const ", "let ", "var "):
        if stripped.startswith(prefix):
            return stripped[len(prefix):].split("(", 1)[0].split("=", 1)[0].split()[0]
    return None


def scan_text_symbols(source: SourceFile) -> list[Finding]:
    rows = []
    for number, line in enumerate(source.text.splitlines(), 1):
        name = _shell_name(line) if source.suffix == ".sh" else _script_name(line)
        if name:
            rows.append((name, number))
    return _findings(source.relative_path, "top-level", rows)


def scan_json(source: SourceFile) -> list[Finding]:
    duplicates: list[str] = []

    def collect(pairs: list[tuple[str, object]]) -> dict[str, object]:
        value: dict[str, object] = {}
        for key, item in pairs:
            if key in value:
                duplicates.append(key)
            value[key] = item
        return value

    try:
        json.loads(source.text, object_pairs_hook=collect)
    except json.JSONDecodeError as exc:
        return [Finding("json_syntax", source.relative_path, exc.lineno, exc.msg)]
    return [
        Finding("duplicate_json_key", source.relative_path, 1, f"JSON key {key} appears more than once", key)
        for key in sorted(set(duplicates))
    ]
