"""schemacheck.py — required keys and types compiled from core/schema/*.json; one cached load per process.

Generic: it checks plain dicts and never imports Store. Store.validate uses it.
"""
from __future__ import annotations

import datetime as _dt
import functools
import json
from pathlib import Path

_SCHEMA_FILES = {"profile": "profile", "event": "event", "candidate": "candidate", "task": "task-card"}


def _schema_type(spec: dict):
    types = {"string": str, "integer": int, "number": (int, float), "boolean": bool,
             "object": dict, "array": list, "null": type(None)}
    names = spec.get("type", [])
    names = [names] if isinstance(names, str) else names
    out = []
    for name in names:
        typ = types[name]
        out.extend(typ if isinstance(typ, tuple) else (typ,))
    if spec.get("format") in ("date", "date-time") and str in out:
        out.append(_dt.date)
    return out[0] if len(out) == 1 else tuple(out)


def _schema_table(spec: dict) -> dict:
    required = set(spec.get("required", []))
    return {kind: {key: _schema_type(value) for key, value in spec.get("properties", {}).items()
                   if "type" in value and (key in required) == (kind == "required")}
            for kind in ("required", "optional")}


@functools.lru_cache(maxsize=16)
def _schema_tables(kind: str, root: str) -> tuple[dict, dict]:
    # JSON files own required keys and types. Compile once per process, keeping hook I/O bounded.
    path = Path(root) / "core/schema" / (_SCHEMA_FILES[kind] + ".schema.json")
    schema = json.loads(path.read_text(encoding="utf-8"))
    item = schema.get("$defs", {}).get("item" if kind == "profile" else "criterion", {})
    return _schema_table(schema), _schema_table(item)


def _check_obj(schema: dict, obj: dict, prefix: str, errors: list[str]) -> None:
    for key, typ in schema["required"].items():
        if key not in obj:
            errors.append(f"{prefix}{key}: 必須キーがありません")
        elif not _is_type(obj[key], typ):
            errors.append(f"{prefix}{key}: 型が不正です（{type(obj[key]).__name__}）")
    for key, typ in schema["optional"].items():
        if key in obj and not _is_type(obj[key], typ):
            errors.append(f"{prefix}{key}: 型が不正です（{type(obj[key]).__name__}）")


def _is_type(value, typ) -> bool:
    if typ is int:
        return isinstance(value, int) and not isinstance(value, bool)
    if isinstance(typ, tuple) and int in typ and float in typ:
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, typ)
