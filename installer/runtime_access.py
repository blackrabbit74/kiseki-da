"""Check state access in the executing process, including host sandbox limits.

This helper is also embedded in project entries for fixed-core compatibility.
"""
import contextlib
import io
import os
from pathlib import Path
import sys
import tempfile


def permission_help(home):
    return (f"Kiseki DAの保存先への書き込み権限を確認してください: {home}\n"
            "検索・文脈取得も履歴を保存します。ホストの権限確認で今回のCLI操作を許可し、"
            "同じ保存先・引数・--sidで再実行してください。\n"
            "許可後にaccessを同じ実行環境で確認し、元の操作の結果を検証してください。\n")


def check_access(home):
    """Mode bits alone do not detect sandbox denial; use a disposable file."""
    home = Path(home).expanduser().resolve()
    try:
        fd, raw = tempfile.mkstemp(prefix=".kiseki-access-", dir=home)
        path = Path(raw)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                stream.write("kiseki-access\n")
                stream.flush()
                os.fsync(stream.fileno())
        finally:
            path.unlink(missing_ok=True)
    except OSError as exc:
        return {"status": "unavailable", "home": str(home), "error": str(exc),
                "next": permission_help(home) if isinstance(exc, PermissionError)
                else "保存先の存在とOSのエラー内容を確認してください。"}
    return {"status": "writable", "home": str(home),
            "scope": "このプロセスによる保存先直下の一時ファイル作成・書込・削除。個々の既存ファイルは元の操作で検証する。"}


def run_with_permission_help(callback, home):
    """Preserve output and status; never elevate or retry implicitly."""
    output = io.StringIO()
    denied = False
    try:
        with contextlib.redirect_stderr(output):
            try:
                code = callback()
            except PermissionError as exc:
                denied = True
                print(str(exc), file=sys.stderr)
                code = 2
    finally:
        text = output.getvalue()
        sys.stderr.write(text)
    if code and (denied or "PermissionError:" in text or "Operation not permitted" in text
                 or "Permission denied" in text):
        sys.stderr.write(permission_help(home))
    return code
