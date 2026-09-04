"""Optional, explicit, reversible host security defaults.

Plugin installation never calls this module unless the user selected
``recommended``.  Whole-file originals are retained and restoration refuses to
overwrite a file that changed after Kiseki DA applied it.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

from .transaction import Transaction
from .util import InstallerError, read_json


CLAUDE_DENY = (
    "Bash(rm -rf /)",
    "Bash(rm -rf ~)",
    "Bash(rm -rf $HOME)",
    "Bash(git push --force origin main)",
    "Bash(git push --force origin master)",
    "Bash(chmod 777:*)",
    "Read(~/.ssh/**)",
    "Read(~/.aws/**)",
    "Read(./.env)",
)


def config_path(host: str) -> Path:
    if host == "claude-code":
        root = Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude"))
        return root.expanduser().resolve() / "settings.json"
    if host == "codex":
        root = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
        return root.expanduser().resolve() / "config.toml"
    raise InstallerError(f"未対応hostです: {host}")


def _hash_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _read(path: Path) -> bytes | None:
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise InstallerError(f"host設定を読めません: {path}: {exc}") from None


def _recommended(host: str, raw: bytes | None) -> str:
    if host == "claude-code":
        try:
            data = json.loads(raw.decode("utf-8")) if raw else {}
        except (UnicodeDecodeError, ValueError) as exc:
            raise InstallerError(f"Claude settings.jsonを読めません: {exc}") from None
        if not isinstance(data, dict):
            raise InstallerError("Claude settings.jsonはJSONオブジェクトである必要があります。")
        permissions = data.setdefault("permissions", {})
        if not isinstance(permissions, dict):
            raise InstallerError("Claude settings.jsonのpermissionsがオブジェクトではありません。")
        permissions["defaultMode"] = "default"
        existing = permissions.get("deny", [])
        if not isinstance(existing, list) or not all(isinstance(item, str) for item in existing):
            raise InstallerError("Claude settings.jsonのpermissions.denyが文字列配列ではありません。")
        permissions["deny"] = list(dict.fromkeys([*existing, *CLAUDE_DENY]))
        return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"

    text = raw.decode("utf-8") if raw else ""
    table = re.search(r"(?m)^\s*\[", text)
    split = table.start() if table else len(text)
    head, tail = text[:split], text[split:]

    def set_key(current: str, key: str, value: str) -> str:
        pattern = re.compile(rf'(?m)^\s*{re.escape(key)}\s*=\s*[^\n]*(?:\n|$)')
        replacement = f'{key} = "{value}"\n'
        if pattern.search(current):
            return pattern.sub(replacement, current)
        if current and not current.endswith("\n"):
            current += "\n"
        return current + replacement

    head = set_key(head, "approval_policy", "on-request")
    head = set_key(head, "sandbox_mode", "workspace-write")
    if tail and head and not head.endswith("\n\n"):
        head += "\n"
    return head + tail


def preview(hosts: list[str]) -> list[dict[str, Any]]:
    result = []
    for host in hosts:
        path = config_path(host)
        raw = _read(path)
        applied = _recommended(host, raw)
        changes: list[dict[str, Any]] = []
        if host == "claude-code":
            data = json.loads(raw.decode("utf-8")) if raw else {}
            permissions = data.get("permissions") if isinstance(data.get("permissions"), dict) else {}
            deny = permissions.get("deny") if isinstance(permissions.get("deny"), list) else []
            changes.append({"key": "permissions.defaultMode",
                            "before": permissions.get("defaultMode", "<unset>"), "after": "default"})
            changes.append({"key": "permissions.deny", "add": [item for item in CLAUDE_DENY if item not in deny]})
        else:
            text = raw.decode("utf-8") if raw else ""
            table = re.search(r"(?m)^\s*\[", text)
            head = text[:table.start()] if table else text
            for key, after in (("approval_policy", "on-request"), ("sandbox_mode", "workspace-write")):
                match = re.search(rf'(?m)^\s*{key}\s*=\s*["\']([^"\']*)["\']', head)
                changes.append({"key": key, "before": match.group(1) if match else "<unset>", "after": after})
        result.append({
            "host": host,
            "path": str(path),
            "before": _hash_bytes(raw or b""),
            "after": _hash_bytes(applied.encode("utf-8")),
            "changes": changes,
        })
    return result


def apply(tx: Transaction, home: Path, host: str) -> dict[str, Any]:
    path = config_path(host)
    raw = _read(path)
    applied = _recommended(host, raw)
    backup_dir = home / "security-backups" / host
    original_path = backup_dir / "original"
    record_path = backup_dir / "record.json"
    existing = read_json(record_path, {})
    if isinstance(existing, dict) and existing.get("managed"):
        current = _read(path)
        if current is not None and _hash_bytes(current) == existing.get("applied_sha256"):
            return existing
        raise InstallerError(f"{host}設定はKiseki DA適用後に変更されています。自動上書きしません: {path}")
    if raw is not None:
        tx.write_text(original_path, raw.decode("utf-8"), mode=0o600)
    record = {
        "schema": 1,
        "managed": True,
        "host": host,
        "path": str(path),
        "original_kind": "file" if raw is not None else "absent",
        "original_sha256": _hash_bytes(raw or b""),
        "original": str(original_path) if raw is not None else None,
        "applied_sha256": _hash_bytes(applied.encode("utf-8")),
    }
    tx.write_json(record_path, record, mode=0o600)
    tx.write_external_text(path, applied)
    return record


def validate_restore(records: dict[str, Any], hosts: list[str]) -> None:
    for host in hosts:
        record = records.get(host)
        if not isinstance(record, dict) or not record.get("managed"):
            continue
        path = Path(record["path"])
        current = _read(path)
        if current is None or _hash_bytes(current) != record.get("applied_sha256"):
            raise InstallerError(
                f"{host}設定はKiseki DA適用後に変更されています。安全のためuninstallを停止しました: {path}"
            )
        if record.get("original_kind") == "file":
            original = Path(str(record.get("original", "")))
            original_raw = _read(original)
            if original_raw is None or _hash_bytes(original_raw) != record.get("original_sha256"):
                raise InstallerError(f"{host}設定の復元用backupが不整合です: {original}")


def restore(tx: Transaction, records: dict[str, Any], host: str) -> None:
    record = records.get(host)
    if not isinstance(record, dict) or not record.get("managed"):
        return
    path = Path(record["path"])
    if record.get("original_kind") == "absent":
        tx.remove_external(path)
    else:
        original = Path(record["original"])
        raw = original.read_text(encoding="utf-8")
        tx.write_external_text(path, raw)
