from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class JsonSecretReference:
    file_path: Path
    key_path: tuple[str, ...]


def parse_json_secret_reference(value: str) -> JsonSecretReference:
    prefix = "secrets_json:"
    if not value.startswith(prefix) or "::" not in value:
        raise ValueError("unsupported secret reference")
    location, dotted_key = value[len(prefix) :].split("::", 1)
    expanded = os.path.expandvars(os.path.expanduser(location))
    file_path = Path(expanded).resolve()
    home = Path.home().resolve()
    if file_path != home and home not in file_path.parents:
        raise ValueError("secret reference must resolve inside the current user home")
    key_path = tuple(part for part in dotted_key.split(".") if part)
    if not key_path:
        raise ValueError("secret reference has no key path")
    return JsonSecretReference(file_path=file_path, key_path=key_path)


def _load_private_json(path: Path, *, create: bool = False) -> dict[str, Any]:
    if not path.exists() and create:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        path.write_text("{}\n", encoding="utf-8")
        os.chmod(path, 0o600)
    if not path.is_file():
        raise FileNotFoundError("private secret file is missing")
    stat = path.stat()
    if stat.st_uid != os.getuid() or (stat.st_mode & 0o777) != 0o600:
        raise PermissionError("private secret file ownership or mode is invalid")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("private secret file must contain a JSON object")
    return value


def resolve_json_secret(value: str) -> str:
    reference = parse_json_secret_reference(value)
    current: Any = _load_private_json(reference.file_path)
    for key in reference.key_path:
        if not isinstance(current, dict) or key not in current:
            raise KeyError("secret reference key path is missing")
        current = current[key]
    if not isinstance(current, str) or not current:
        raise ValueError("secret reference does not resolve to a non-empty string")
    return current


def set_json_secret(value: str, replacement: str) -> None:
    if not replacement:
        raise ValueError("replacement secret must not be empty")
    reference = parse_json_secret_reference(value)
    payload = _load_private_json(reference.file_path, create=True)
    current: dict[str, Any] = payload
    for key in reference.key_path[:-1]:
        child = current.get(key)
        if child is None:
            child = {}
            current[key] = child
        if not isinstance(child, dict):
            raise ValueError("secret reference traverses a non-object value")
        current = child
    current[reference.key_path[-1]] = replacement
    temporary = reference.file_path.with_name(reference.file_path.name + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.chmod(temporary, 0o600)
    json.loads(temporary.read_text(encoding="utf-8"))
    os.replace(temporary, reference.file_path)
    os.chmod(reference.file_path, 0o600)
