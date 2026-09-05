"""Portable plugin hook launcher for Claude Code and Codex.

This wrapper is deliberately tiny: it locates the plugin root, validates the
requested normalized hook event and delegates to the version-matched runtime.
The runtime's hook command keeps the fail-open, zero-exit contract.
"""
from __future__ import annotations

import os
from pathlib import Path
import runpy
import stat
import sys

sys.dont_write_bytecode = True


EVENTS = {"user-input", "session-start", "pre-tool", "post-tool", "stop", "session-end"}
ENVS = {"claude-code", "codex"}


def _plugin_root() -> Path:
    configured = os.environ.get("PLUGIN_ROOT") or os.environ.get("CLAUDE_PLUGIN_ROOT")
    return Path(configured).resolve() if configured else Path(__file__).resolve().parents[1]


def _configure_state_home() -> bool:
    """Resolve a custom home for GUI hosts without trusting arbitrary files.

    An inherited environment variable always wins.  The stable pointer is a
    single, private, regular file written by the installer; malformed or
    permissive pointers cause the hook to fail open without touching state.
    """
    if os.environ.get("KISEKI_DA_HOME"):
        return True
    configured = os.environ.get("KISEKI_DA_POINTER")
    pointer = (Path(configured).expanduser() if configured else Path.home() / ".kiseki-da-location").absolute()
    if not pointer.exists():
        # The supported installer always creates this pointer, including for
        # the default home. Missing means activation cannot be resolved safely;
        # fail open without falling through to a second default state.
        return False
    try:
        info = pointer.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_size <= 0 or info.st_size > 4096:
            return False
        if os.name != "nt":
            if hasattr(os, "getuid") and info.st_uid != os.getuid():
                return False
            if info.st_mode & 0o022:
                return False
        raw = pointer.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return False
    lines = raw.splitlines()
    if len(lines) != 1 or not raw.endswith("\n") or lines[0] != lines[0].strip() or "\x00" in lines[0]:
        return False
    home = Path(lines[0])
    if not home.is_absolute():
        return False
    home = home.resolve(strict=False)
    if not home.is_dir():
        return False
    os.environ["KISEKI_DA_HOME"] = str(home)
    return True


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 2 or args[0] not in EVENTS or args[1] not in ENVS:
        return 0
    if not (3, 11) <= sys.version_info[:2] <= (3, 14):
        return 0
    if not _configure_state_home():
        return 0
    target = _plugin_root() / "core" / "ctx" / "cli.py"
    if not target.is_file():
        return 0
    sys.argv = [str(target), "hook", args[0], "--env", args[1]]
    try:
        runpy.run_path(str(target), run_name="__main__")
    except SystemExit as exc:
        return int(exc.code or 0)
    except BaseException:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
