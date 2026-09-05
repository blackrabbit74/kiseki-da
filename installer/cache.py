"""Select one native Codex cache while keeping every running hook path resolvable."""
from __future__ import annotations

import ctypes
import os
from pathlib import Path
import shutil
import sys
import tempfile


def _exchange(left: Path, right: Path) -> None:
    """Atomically swap a directory and an alias; never leave the hook path absent."""
    libc = ctypes.CDLL(None, use_errno=True)
    if sys.platform == "darwin":
        function = libc.renamex_np
        function.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
        result = function(os.fsencode(left), os.fsencode(right), 2)  # RENAME_SWAP
    elif sys.platform.startswith("linux") and hasattr(libc, "renameat2"):
        function = libc.renameat2
        function.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        result = function(-100, os.fsencode(left), -100, os.fsencode(right), 2)  # RENAME_EXCHANGE
    else:
        raise OSError("このOSではhook pathを保つatomic cache切替を利用できません。")
    if result != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))


def check_exchange(parent: Path) -> None:
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".cache-exchange-", dir=parent) as raw:
        root = Path(raw)
        (root / "target").mkdir()
        (root / "directory").mkdir()
        (root / "link").symlink_to(root / "target", target_is_directory=True)
        _exchange(root / "directory", root / "link")
        if not (root / "directory").is_symlink() or not (root / "link").is_dir():
            raise OSError("atomic cache切替の検証に失敗しました。")


def _files(root: Path) -> dict[str, bytes]:
    return {str(path.relative_to(root)): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def select_cache(active: Path, retained: Path) -> None:
    """Codex lists real version directories; aliases preserve inactive hook paths."""
    active = active.absolute()
    retained = retained.resolve()
    if not active.is_dir():
        raise OSError(f"選択するcacheがありません: {active}")
    check_exchange(active.parent)
    if active.is_symlink():
        # Restore a real directory without ever unlinking the version path.
        with tempfile.TemporaryDirectory(prefix=".cache-select-", dir=active.parent) as raw:
            replacement = Path(raw) / "version"
            shutil.copytree(active.resolve(), replacement, symlinks=True)
            _exchange(active, replacement)
    for candidate in sorted(active.parent.iterdir()):
        if candidate == active or candidate.is_symlink() or not candidate.is_dir() or candidate.name.startswith("."):
            continue
        if not (candidate / ".codex-plugin/plugin.json").is_file():
            continue
        archive = retained / candidate.name
        if archive.exists():
            if _files(archive) != _files(candidate):
                raise OSError(f"保存済みcacheと内容が一致しません: {candidate}")
        else:
            archive.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix=".cache-retain-", dir=archive.parent) as raw:
                staged = Path(raw) / "version"
                shutil.copytree(candidate, staged, symlinks=True)
                os.rename(staged, archive)
        with tempfile.TemporaryDirectory(prefix=".cache-alias-", dir=active.parent) as raw:
            alias = Path(raw) / "version"
            alias.symlink_to(archive, target_is_directory=True)
            _exchange(candidate, alias)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: cache.py ACTIVE_CACHE RETAINED_ROOT")
    select_cache(Path(sys.argv[1]), Path(sys.argv[2]))
