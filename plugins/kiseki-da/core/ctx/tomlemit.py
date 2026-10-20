"""tomlemit.py — minimal TOML emitter for the shapes Kiseki DA writes (scalars, tables, array tables).

Generic: it knows no profile sections; store.emit_toml passes them in as `omit_empty`.
"""
from __future__ import annotations

import datetime as _dt
import re

_BARE_KEY = re.compile(r"^[A-Za-z0-9_-]+$")


def _toml_key(k: str) -> str:
    return k if _BARE_KEY.match(k) else _toml_str(k)


def _toml_str(s: str) -> str:
    out = ['"']
    for ch in s:
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\t":
            out.append("\\t")
        elif ch == "\b":
            out.append("\\b")
        elif ch == "\f":
            out.append("\\f")
        elif ord(ch) < 0x20 or ch == "\x7f":
            out.append(f"\\u{ord(ch):04X}")
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def _toml_value(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        if v != v or v in (float("inf"), float("-inf")):
            raise ValueError("non-finite float is not representable")
        return repr(v)
    if isinstance(v, _dt.datetime):
        if v.tzinfo is None:  # TOML local date-time from a hand edit: local time, as parse_ts reads it
            v = v.astimezone()
        return v.isoformat()
    if isinstance(v, _dt.date):
        return v.isoformat()
    if isinstance(v, _dt.time):
        return v.isoformat()
    if isinstance(v, str):
        return _toml_str(v)
    if isinstance(v, (list, tuple)):
        return "[" + ", ".join(_toml_value(x) for x in v) + "]"
    if isinstance(v, dict):
        values = [f"{_toml_key(str(k))} = {_toml_value(value)}"
                  for k, value in v.items() if value is not None]
        return "{ " + ", ".join(values) + " }"
    raise TypeError(f"unsupported TOML value: {type(v).__name__}")


def emit_toml(data: dict, omit_empty: tuple[str, ...] = ()) -> str:
    """Minimal emitter: (a) top-level scalars, (b) one-level tables, (c) array tables.

    Empty top-level lists are written as `key = []`, except under the keys in `omit_empty`, which are omitted.
    None values inside items are skipped.
    """
    scalars: list[tuple[str, object]] = []
    tables: list[tuple[str, dict]] = []
    arrays: list[tuple[str, list]] = []
    for k, v in data.items():
        if v is None:
            continue
        if isinstance(v, dict):
            tables.append((k, v))
        elif isinstance(v, list) and v and all(isinstance(x, dict) for x in v):
            arrays.append((k, v))
        elif isinstance(v, list) and not v:
            if k not in omit_empty:
                scalars.append((k, v))
        else:
            scalars.append((k, v))
    out: list[str] = []
    for k, v in scalars:
        out.append(f"{_toml_key(k)} = {_toml_value(v)}")
    for k, tbl in tables:
        if out:
            out.append("")
        out.append(f"[{_toml_key(k)}]")
        for kk, vv in tbl.items():
            if vv is None:
                continue
            out.append(f"{_toml_key(kk)} = {_toml_value(vv)}")
    for k, items in arrays:
        for item in items:
            out.append("")
            out.append(f"[[{_toml_key(k)}]]")
            for kk, vv in item.items():
                if vv is None:
                    continue
                out.append(f"{_toml_key(kk)} = {_toml_value(vv)}")
    return "\n".join(out) + "\n"
