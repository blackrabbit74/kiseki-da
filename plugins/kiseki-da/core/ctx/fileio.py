"""fileio.py — file primitives for state under KISEKI_DA_HOME: atomic write, JSONL append/read, locks.

Generic: nothing here knows about profiles, events or Store. store.py re-exports these names.
"""
from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path
from typing import Iterator

try:
    import fcntl as _fcntl
except ImportError:  # Windows
    _fcntl = None
try:
    import msvcrt as _msvcrt
except ImportError:  # POSIX
    _msvcrt = None


def dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / f".{path.name}.{os.getpid()}.tmp"
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _append_jsonl(path: Path, rec: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(dumps(rec) + "\n")


def _lock(fd: int) -> bool:
    """Take an exclusive advisory lock on `fd` (blocking). False when the platform has none."""
    try:
        if _fcntl is not None:
            _fcntl.flock(fd, _fcntl.LOCK_EX)
            return True
        if _msvcrt is not None:
            os.lseek(fd, 0, os.SEEK_SET)
            _msvcrt.locking(fd, _msvcrt.LK_LOCK, 1)
            return True
    except OSError:
        pass
    return False


def _unlock(fd: int) -> None:
    try:
        if _fcntl is not None:
            _fcntl.flock(fd, _fcntl.LOCK_UN)
        elif _msvcrt is not None:
            os.lseek(fd, 0, os.SEEK_SET)
            _msvcrt.locking(fd, _msvcrt.LK_UNLCK, 1)
    except OSError:
        pass


@contextlib.contextmanager
def _locked_append(path: Path) -> Iterator:
    """Open `path` for appending and hold an exclusive lock on it for the block.

    Concurrent hook processes of one session (parallel tool calls) share `session/<sid>.seq`;
    the lock on the append-only file (its inode is never replaced) serialises
    read-increment-write of the counter and the JSONL append. Best effort: without a usable
    lock the block still runs.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        locked = _lock(f.fileno())
        try:
            yield f
            f.flush()
        finally:
            if locked:
                _unlock(f.fileno())


def _iter_jsonl(path: Path) -> Iterator[dict]:
    if not path.exists():
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if isinstance(rec, dict):
                yield rec
