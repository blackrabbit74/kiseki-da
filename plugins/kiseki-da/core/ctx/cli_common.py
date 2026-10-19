"""cli_common.py — output and Store helpers shared by every CLI command module.

They are not in cli.py because `python3 core/ctx/cli.py` runs that file as __main__: a command module
importing cli would load the same file a second time as core.ctx.cli.
"""
from __future__ import annotations

import sys
from pathlib import Path

from core.ctx import store as _store
from core.ctx.store import Store, UserError, dumps


def _err(msg: str) -> None:
    sys.stderr.write(msg.rstrip("\n") + "\n")


def _out(text: str) -> None:
    if text and not text.endswith("\n"):
        text += "\n"
    sys.stdout.write(text)


def _emit_json(obj) -> None:
    sys.stdout.write(dumps(obj) + "\n")


def _json(args) -> bool:
    return bool(getattr(args, "json", False))


def _make_store(args) -> Store:
    store = Store.for_cwd(Path.cwd(), home=_store.kiseki_da_home(), sid=getattr(args, "sid", None))
    if store is None:
        raise UserError("このディレクトリはKiseki DAのproject scopeに登録されていません")
    # Fail before any command-specific write when concurrent host sessions make
    # implicit event attribution ambiguous.
    store.effective_sid()
    return store


def _common_store(args) -> Store:
    return Store(home=_store.kiseki_da_home(), sid=getattr(args, "sid", None))


def _confirm_text(label: str) -> bool:
    try:
        return input(f"{label} [y/N]: ").strip().casefold() in {"y", "yes"}
    except EOFError:
        return False
