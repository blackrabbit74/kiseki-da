"""Small cross-platform filesystem and JSON helpers."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any, Iterable


class InstallerError(Exception):
    """A user-facing installer error."""


def kiseki_home() -> Path:
    raw = os.environ.get("KISEKI_DA_HOME")
    return (Path(raw).expanduser() if raw else Path.home() / ".kiseki-da").resolve()


def kiseki_pointer_path() -> Path:
    """Stable location read by GUI-launched hooks when HOME was customized."""
    raw = os.environ.get("KISEKI_DA_POINTER")
    return (Path(raw).expanduser() if raw else Path.home() / ".kiseki-da-location").absolute()


def location_pointer_text(home: Path) -> str:
    resolved = home.expanduser().resolve()
    if not resolved.is_absolute() or "\x00" in str(resolved) or "\n" in str(resolved) or "\r" in str(resolved):
        raise InstallerError(f"KISEKI_DA_HOMEを安全なpointerにできません: {home}")
    return str(resolved) + "\n"


def atomic_write_text(path: Path, text: str, *, mode: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    tmp = Path(raw)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        if mode is not None:
            os.chmod(tmp, mode)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def atomic_write_json(path: Path, value: Any, *, mode: int | None = None) -> None:
    atomic_write_text(path, json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", mode=mode)


def read_json(path: Path, default: Any = None) -> Any:
    try:
        with path.open(encoding="utf-8") as stream:
            return json.load(stream)
    except FileNotFoundError:
        return default
    except (OSError, ValueError) as exc:
        raise InstallerError(f"JSONを読めません: {path}: {exc}") from None


def load_answers(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    value = read_json(Path(path).expanduser().resolve())
    if not isinstance(value, dict):
        raise InstallerError("--answers はJSONオブジェクトのファイルを指定してください。")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_checksum(archive: Path, checksum: str | Path) -> None:
    expected: str | None = None
    raw_path = Path(checksum)
    if raw_path.exists():
        for line in raw_path.read_text(encoding="utf-8").splitlines():
            parts = line.strip().split()
            if len(parts) >= 2 and Path(parts[-1].lstrip("*")) .name == archive.name:
                expected = parts[0]
                break
        if expected is None:
            raise InstallerError(f"SHA256SUMS に {archive.name} がありません。")
    else:
        expected = str(checksum).strip()
    if not re.fullmatch(r"[0-9a-fA-F]{64}", expected or ""):
        raise InstallerError("SHA-256値の形式が不正です。")
    actual = sha256_file(archive)
    if actual.lower() != expected.lower():
        raise InstallerError(f"SHA-256が一致しません: expected={expected.lower()} actual={actual}")


def copytree_filtered(source: Path, destination: Path) -> None:
    from .constants import RUNTIME_EXCLUDES

    shutil.copytree(
        source,
        destination,
        ignore=lambda _dir, names: [name for name in names if name in RUNTIME_EXCLUDES or name.endswith(".pyc")],
    )


def remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
    elif path.exists():
        shutil.rmtree(path)


def command_display(argv: Iterable[str]) -> str:
    """Readable command rendering for plans/journals; it is never executed."""
    values = []
    for value in argv:
        value = str(value)
        values.append(json.dumps(value, ensure_ascii=False) if re.search(r"\s", value) else value)
    return " ".join(values)


_SECRET_PATTERNS = (
    (re.compile(r"(?i)(\bBearer\s+)[^\s]+"), r"\1[REDACTED]"),
    (re.compile(r"(?i)((?:api[_-]?key|access[_-]?token|password|secret|認証情報|秘密鍵)\s*(?:=|:|：|は)\s*)[^\s]+"),
     r"\1[REDACTED]"),
    (re.compile(r"(?i)(--(?:api[_-]?key|token|password)\s+)[^\s]+"), r"\1[REDACTED]"),
    (re.compile(r"(https?://)[^\s/:@]+:[^\s/@]+@"), r"\1[REDACTED]@"),
    (re.compile(r"\b(?:sk-[A-Za-z0-9_-]{10,}|gh[pousr]_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16})\b"),
     "[REDACTED]"),
    (re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
     "[REDACTED PRIVATE KEY]"),
)


def redact_sensitive(value: object) -> str:
    text = str(value if value is not None else "")
    for pattern, replacement in _SECRET_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def parse_version(text: str) -> tuple[int, int, int] | None:
    match = re.search(r"(?<!\d)(\d+)\.(\d+)\.(\d+)", text)
    return tuple(map(int, match.groups())) if match else None
