#!/usr/bin/env python3
"""cli.py — the Kiseki DA runtime command entry point.

Command handlers live in cmd_task.py, cmd_memory.py, cmd_persona.py and cmd_admin.py (helpers shared by
them in cli_common.py); the heavier modules they use are imported lazily inside each command. This file
keeps the entry point, the parser and the fail-open hook wrapper. `hook` never exits non-zero
(fail-open). Other commands exit 1 on a UserError, 2 on an unexpected internal error (nothing is rolled
back, unlike the installer's 2) and 130 on interrupt.
"""
from __future__ import annotations

import sys
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import argparse  # noqa: E402
import contextlib  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402
import re  # noqa: E402
import types  # noqa: E402

from core.ctx import store as _store  # noqa: E402
from core.ctx import cli_common, cmd_admin, cmd_memory, cmd_persona, cmd_task  # noqa: E402
from core.ctx.cli_common import _err  # noqa: E402
from core.ctx.cmd_task import (  # noqa: E402
    cmd_task_brief, cmd_task_close, cmd_task_defer, cmd_task_list, cmd_task_new, cmd_task_override,
    cmd_task_set, cmd_task_show, cmd_verify_run,
)
from core.ctx.cmd_memory import (  # noqa: E402
    cmd_approve, cmd_candidate_add, cmd_candidate_list, cmd_capture, cmd_context, cmd_reject,
    cmd_remember, cmd_search,
)
from core.ctx.cmd_persona import (  # noqa: E402
    cmd_persona_edit, cmd_persona_preview, cmd_persona_reset, cmd_persona_show, cmd_setup,
)
from core.ctx.cmd_admin import (  # noqa: E402
    cmd_build, cmd_evals_run, cmd_init, cmd_log, cmd_policy, cmd_project_add, cmd_project_list,
    cmd_project_remove, cmd_report, cmd_session_clear, cmd_session_list,
)
from core.ctx.store import Store, UserError  # noqa: E402

HOOK_EVENTS = ("session-start", "user-input", "pre-tool", "post-tool", "stop", "session-end")
ENVS = ("claude-code", "codex")


# argparse's English error texts → Japanese (CLI text is Japanese only, see CLAUDE.md). Same wording on
# Python 3.11–3.14. A text no pattern matches keeps the `引数が不正です:` prefix and argparse's wording.
_ARGPARSE_JA: tuple[tuple[str, str], ...] = (
    (r"the following arguments are required: (?P<a>.+)", "{a} を指定してください"),
    (r"one of the arguments (?P<a>.+) is required", "{a} のいずれかを指定してください"),
    (r"unrecognized arguments: (?P<a>.+)", "不明な引数です: {a}"),
    (r"ambiguous option: (?P<a>\S+) could match (?P<b>.+)", "{a} は曖昧です（候補: {b}）"),
    (r"argument (?P<a>.+?): invalid choice: (?P<v>.+?) \(choose from (?P<c>.+)\)", "{a} は {c} のいずれかです（指定値: {v}）"),
    (r"argument (?P<a>.+?): invalid int value: (?P<v>.+)", "{a} は整数で指定してください（指定値: {v}）"),
    (r"argument (?P<a>.+?): invalid float value: (?P<v>.+)", "{a} は数値で指定してください（指定値: {v}）"),
    (r"argument (?P<a>.+?): invalid (?P<t>\S+) value: (?P<v>.+)", "{a} の値が不正です（{t}、指定値: {v}）"),
    (r"argument (?P<a>.+?): not allowed with argument (?P<b>.+)", "{a} と {b} は同時に指定できません"),
    (r"argument (?P<a>.+?): expected (?:one|at least one) argument", "{a} に値がありません"),
    (r"argument (?P<a>.+?): expected (?P<n>\d+) arguments?", "{a} には値が {n} 個必要です"),
    (r"argument (?P<a>.+?): ignored explicit argument (?P<v>.+)", "{a} は値を取りません（指定値: {v}）"),
)
_SUBCOMMAND_METAVARS = ("<cmd>", "<sub>")


class _Formatter(argparse.HelpFormatter):
    """argparse help with a Japanese usage prefix."""

    def add_usage(self, usage, actions, groups, prefix=None):
        super().add_usage(usage, actions, groups, "使い方: " if prefix is None else prefix)


class _Parser(argparse.ArgumentParser):
    """argparse errors become UserError (exit 1, one Japanese line) instead of exit 2; help text is Japanese."""

    def __init__(self, *args, **kwargs):
        want_help = kwargs.pop("add_help", True)
        kwargs.setdefault("formatter_class", _Formatter)
        super().__init__(*args, add_help=False, **kwargs)
        self._positionals.title = "引数"
        self._optionals.title = "オプション"
        if want_help:
            self.add_argument("-h", "--help", action="help", default=argparse.SUPPRESS,
                              help="このヘルプを表示して終了する")

    def error(self, message: str):  # noqa: D401
        if message in {f"the following arguments are required: {m}" for m in _SUBCOMMAND_METAVARS}:
            raise UserError(f"引数が不正です: サブコマンドを指定してください（一覧: {self.prog} -h）")
        for pattern, template in _ARGPARSE_JA:
            m = re.fullmatch(pattern, message)
            if m:
                message = template.format(**m.groupdict())
                break
        raise UserError(f"引数が不正です: {message}")


# ---------------------------------------------------------------- small helpers

def _utf8_stdio() -> None:
    """Force UTF-8 on stdin / stdout / stderr. Every reason and message is Japanese, and under a non-UTF-8
    locale codec a hook deny would otherwise die in the text layer and fail open as an empty (allow) stdout."""
    for name in ("stdin", "stdout", "stderr"):
        reconfigure = getattr(getattr(sys, name, None), "reconfigure", None)
        if reconfigure is None:  # replaced stream (tests, redirect_stdout): nothing to reconfigure
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):  # already read from / closed: keep the current codec
            pass


@contextlib.contextmanager
def _using_home(args):
    old = os.environ.get("KISEKI_DA_HOME")
    value = getattr(args, "home", None)
    if value:
        os.environ["KISEKI_DA_HOME"] = str(Path(value).expanduser().resolve())
    try:
        yield
    finally:
        if value:
            if old is None:
                os.environ.pop("KISEKI_DA_HOME", None)
            else:
                os.environ["KISEKI_DA_HOME"] = old


# ---------------------------------------------------------------- hook (fail-open)

def _hook_where(argv: list[str]) -> str:
    ev = argv[1] if len(argv) > 1 and not argv[1].startswith("-") else "unknown"
    return f"hook:{ev}"


def _record_hook_error(where: str, exc: BaseException, payload: dict | None = None) -> None:
    if not isinstance(payload, dict):
        return
    cwd = payload.get("cwd") if isinstance(payload.get("cwd"), str) else None
    roots = payload.get("workspace_roots")
    if not cwd and isinstance(roots, list) and roots and isinstance(roots[0], str):
        cwd = roots[0]
    if not cwd:
        return
    sid = payload.get("conversation_id") or payload.get("session_id")
    try:
        store = Store.for_cwd(cwd, home=_store.kiseki_da_home(), sid=str(sid) if sid else None)
        if store is not None:
            store.append_event({"type": "error", "where": where,
                                "message": f"{type(exc).__name__}: {exc}"[:500]})
    except BaseException:  # noqa: BLE001 — best effort only
        pass


def _run_hook(args, raw: str | None = None) -> int:
    from core.ctx import hooks
    raw = sys.stdin.read() if raw is None else raw
    payload = json.loads(raw) if raw.strip() else {}
    if not isinstance(payload, dict):
        raise ValueError("hook payload is not a JSON object")
    hi = hooks.parse_input(payload, args.env, args.event)
    st = Store(sid=hi.sid)
    out = hooks.handle(st, hi)
    stdout, stderr, code = hooks.format_output(hi, out)
    if stdout:
        sys.stdout.write(stdout)
    if stderr:
        sys.stderr.write(stderr)
    sys.stdout.flush()
    return int(code or 0)


def cmd_hook(args, raw: str | None = None) -> int:
    raw = sys.stdin.read() if raw is None else raw
    payload = None
    try:
        parsed = json.loads(raw) if raw.strip() else {}
        payload = parsed if isinstance(parsed, dict) else None
    except ValueError:
        pass
    try:
        return _run_hook(args, raw)
    except BaseException as e:  # noqa: BLE001 — fail open, never non-zero
        _record_hook_error(f"hook:{getattr(args, 'event', 'unknown')}", e, payload)
        return 0


def _hook_main(argv: list[str]) -> int:
    raw = sys.stdin.read()
    payload = None
    try:
        parsed = json.loads(raw) if raw.strip() else {}
        payload = parsed if isinstance(parsed, dict) else None
    except ValueError:
        pass
    try:
        args = build_parser().parse_args(argv)
    except BaseException as e:  # noqa: BLE001 — argparse SystemExit / UserError included
        _record_hook_error(_hook_where(argv), e, payload)
        return 0
    with _using_home(args):
        return cmd_hook(args, raw)


# ---------------------------------------------------------------- parser

def _parent() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help="JSON で出力する")
    p.add_argument("--sid", default=argparse.SUPPRESS, help="セッション ID（省略時は session/current）")
    p.add_argument("--home", default=argparse.SUPPRESS, help="状態領域の絶対パス（KISEKI_DA_HOME より優先）")
    return p


def build_parser() -> argparse.ArgumentParser:
    parent = _parent()
    root = _Parser(prog="kiseki-da", description="Kiseki DA — Digital Assistant", parents=[parent])
    sub = root.add_subparsers(dest="command", metavar="<cmd>", required=True)

    def add(name: str, func, **kw):
        p = sub.add_parser(name, parents=[parent], **kw)
        p.set_defaults(func=func)
        return p

    p = add("init", cmd_init, help="状態ディレクトリを初期化する")
    p.add_argument("--force", action="store_true", help="profile.toml を snapshot してから複製し直す")

    p = add("build", cmd_build, help="常駐ブロックを出力する")
    p.add_argument("--budget", type=int, default=2500)
    p.add_argument("--goals", action="store_true", help="進行中目標を含める")

    p = add("setup", cmd_setup, help="基本情報とキャラクターを初期設定する")
    p.add_argument("--answers", default=None, help="identity/personaを含むJSON")
    p.add_argument("--yes", action="store_true", help="回答ファイルを確認済みとして保存する")
    p.add_argument("--no-preview", action="store_true", help="実モデルプレビューを省略する")
    p.add_argument("--host", action="append", choices=("claude-code", "codex", "all"), default=None)

    persona = add("persona", None, help="キャラクター設定")
    psub = persona.add_subparsers(dest="persona_command", metavar="<sub>", required=True)

    def padd(name: str, func, **kw):
        q = psub.add_parser(name, parents=[parent], **kw)
        q.set_defaults(func=func)
        return q

    padd("show", cmd_persona_show, help="現在のキャラクター設定を表示する")
    p = padd("edit", cmd_persona_edit, help="キャラクター設定を変更する")
    p.add_argument("--answers", default=None, help="persona JSONまたはpersonaキーを含むJSON")
    p.add_argument("--name", default=None)
    p.add_argument("--first-person", dest="first_person", default=None)
    p.add_argument("--user-address", dest="user_address", default=None)
    p.add_argument("--formality", choices=("casual", "balanced", "formal"), default=None)
    p.add_argument("--warmth", choices=("reserved", "balanced", "warm"), default=None)
    p.add_argument("--verbosity", choices=("compact", "balanced", "detailed"), default=None)
    p.add_argument("--initiative", choices=("reactive", "balanced", "proactive"), default=None)
    p.add_argument("--relationship", choices=("neutral", "partner", "secretary", "mentor", "companion", "custom"), default=None)
    p.add_argument("--custom-style", dest="custom_style", default=None)
    p.add_argument("--host", action="append", choices=("claude-code", "codex", "all"), default=None)
    p.add_argument("--no-preview", action="store_true")
    p.add_argument("--live-preview", action="store_true",
                   help="設定を保存する前にモデル提供者へ送って試すことへ明示同意する")
    p.add_argument("--yes", action="store_true")
    p = padd("preview", cmd_persona_preview, help="保存済み設定を実モデルで試す")
    p.add_argument("--host", action="append", choices=("claude-code", "codex", "all"), default=None)
    p = padd("reset", cmd_persona_reset, help="キャラクター設定を空にする")
    p.add_argument("--yes", action="store_true")

    project = add("project", None, help="project scopeを管理する")
    prsub = project.add_subparsers(dest="project_command", metavar="<sub>", required=True)
    p = prsub.add_parser("add", parents=[parent], help="projectを登録する")
    p.set_defaults(func=cmd_project_add)
    p.add_argument("path")
    p.add_argument("--yes", action="store_true")
    p = prsub.add_parser("list", parents=[parent], help="登録projectを表示する")
    p.set_defaults(func=cmd_project_list)
    p = prsub.add_parser("remove", parents=[parent], help="project登録を解除し状態を保持する")
    p.set_defaults(func=cmd_project_remove)
    p.add_argument("selector", help="project UUIDまたはpath")
    p.add_argument("--yes", action="store_true")

    session = add("session", None, help="有効session markerを確認・復旧する")
    ssub = session.add_subparsers(dest="session_command", metavar="<sub>", required=True)
    p = ssub.add_parser("list", parents=[parent], help="有効session markerを表示する")
    p.set_defaults(func=cmd_session_list)
    p = ssub.add_parser("clear", parents=[parent], help="staleなsession markerを明示解除する")
    p.set_defaults(func=cmd_session_clear)
    p.add_argument("selector", help="session idまたはall")
    p.add_argument("--yes", action="store_true")
    ctx = add("context", cmd_context, help="必要な文脈を省略せずページ単位で取得する")
    ctx.add_argument("context_command", choices=("required", "profile", "instruction"))
    ctx.add_argument("--page", type=int, default=1)
    p = add("policy", cmd_policy, help="方針本文を取得する")
    p.add_argument("policy_command", choices=("show",))
    p.add_argument("name", choices=("interaction", "verification", "decision-support", "task-card"))

    p = add("search", cmd_search, help="events / tasks / profile を検索する")
    p.add_argument("query")
    p.add_argument("--k", type=int, default=5)
    p.add_argument("--since", default="180d")
    p.add_argument("--kind", default=None, help="events,tasks,profile,capture のカンマ区切り")
    p.add_argument("--no-decay", action="store_true")

    task = add("task", None, help="タスクカード")
    tsub = task.add_subparsers(dest="task_command", metavar="<sub>", required=True)

    def tadd(name: str, func, **kw):
        q = tsub.add_parser(name, parents=[parent], **kw)
        q.set_defaults(func=func)
        return q

    p = tadd("new", cmd_task_new, help="カードを作る")
    p.add_argument("--goal", required=True)
    p.add_argument("--risk", default="R1")
    p.add_argument("--kind", default="code")
    p.add_argument("--id", default=None)
    p = tadd("show", cmd_task_show, help="カード全文")
    p.add_argument("id")
    p = tadd("list", cmd_task_list, help="カード一覧")
    p.add_argument("--status", default="open", help="open|done|deferred|abandoned|all")
    p = tadd("set", cmd_task_set, help="カードを更新する")
    p.add_argument("id")
    p.add_argument("--status", choices=("open", "abandoned"), default=None)
    p.add_argument("--risk", choices=("R0", "R1", "R2", "R3"), default=None)
    p.add_argument("--workspace", default=None, help="カードの所属案件フォルダを明示して設定する")
    p.add_argument("--constraint", action="append", help="案件の必須制約または対象外を追加する")
    p.add_argument("--next", dest="next_action", default=None, help="次に行う作業を記録する")
    p.add_argument("--add-criterion", action="append", metavar='"<claim> :: <check>"')
    p.add_argument("--evidence", action="append", metavar="<Cn>=<ev:sid:seq>|last|last:<tool>")
    p.add_argument("--assume", default=None)
    p.add_argument("--question", default=None)
    p.add_argument("--decide", default=None)
    p.add_argument("--note", default=None)
    p = tadd("close", cmd_task_close, help="証拠を突合して閉じる")
    p.add_argument("id")
    p = tadd("defer", cmd_task_defer, help="未検証のまま保留する")
    p.add_argument("id")
    p.add_argument("--reason", required=True)
    p = tadd("brief", cmd_task_brief, help="ワーカー指示書を生成する")
    p.add_argument("id")
    p.add_argument("--role", choices=("research", "review"), required=True)
    p.add_argument("--scope", default=None)
    p = tadd("override", cmd_task_override, help="現在の利用者指示を今回の対象操作に結び付ける")
    p.add_argument("id")
    p.add_argument("--quote", required=True, help="最新の利用者発言全文")
    p.add_argument("--command", dest="command_text", default=None, help="今回だけ実行する正確なシェルコマンド")
    p.add_argument("--tool", default=None)
    p.add_argument("--input", dest="tool_input", default=None)

    p = add("log", cmd_log, help="イベントを記録する")
    p.add_argument("type")
    p.add_argument("--data", required=True, help="JSON オブジェクト")

    p = add("capture", cmd_capture, help="外部資料やメモを記録する")
    p.add_argument("text")
    p.add_argument("--source", default=None)

    cand = add("candidate", None, help="記憶候補")
    csub = cand.add_subparsers(dest="candidate_command", metavar="<sub>", required=True)
    p = csub.add_parser("add", parents=[parent], help="候補を追加する")
    p.set_defaults(func=cmd_candidate_add)
    p.add_argument("--text", required=True)
    p.add_argument("--quote", required=True, help="利用者の言葉")
    p.add_argument("--kind", choices=_store.CANDIDATE_KINDS, default="preference")
    p.add_argument("--source", default="inference", help="user-stated|inference|document:<ref>")
    p.add_argument("--key", default=None)
    p = csub.add_parser("list", parents=[parent], help="候補一覧")
    p.set_defaults(func=cmd_candidate_list)
    p.add_argument("--status", choices=_store.CANDIDATE_STATUSES, default=None)

    p = add("approve", cmd_approve, help="候補を承認して profile に入れる")
    p.add_argument("cid")
    p.add_argument("--confidence", type=float, default=None)
    p.add_argument("--review-by", default=None)
    p.add_argument("--supersedes", default=None)
    p.add_argument("--global", dest="global_scope", action="store_true", help="利用者が共通で覚えると明示した場合だけ昇格する")
    p.add_argument("--quote", required=True, help="最新の利用者発言全文")

    p = add("reject", cmd_reject, help="候補を却下する")
    p.add_argument("cid")
    p.add_argument("--reason", default=None)

    p = add("remember", cmd_remember, help="利用者自身が profile に直接追加する")
    p.add_argument("text", nargs="?")
    p.add_argument("--from-user-input", action="store_true", help="/remember の実際の発言から本文を取得する")
    p.add_argument("--kind", choices=_store.CANDIDATE_KINDS, default="preference")
    p.add_argument("--key", default=None)
    p.add_argument("--global", dest="global_scope", action="store_true", help="全案件の共通記憶に保存する（明示指示が必要）")
    p.add_argument("--quote", default=None, help="最新の利用者発言全文")

    p = add("report", cmd_report, help="週次指標 / 監査")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--week", action="store_true")
    g.add_argument("--audit", action="store_true")

    verify = add("verify", None, help="終了状態を記録できる検証command runner")
    vsub = verify.add_subparsers(dest="verify_command", metavar="<sub>", required=True)
    p = vsub.add_parser("run", parents=[parent], help="shellを介さずcommandを実行し証拠eventを残す")
    p.set_defaults(func=cmd_verify_run)
    p.add_argument("--timeout", type=int, default=600)
    p.add_argument("command", nargs=argparse.REMAINDER)

    p = add("hook", cmd_hook, help="環境の hook 入口（stdin に JSON）")
    p.add_argument("event", choices=HOOK_EVENTS)
    p.add_argument("--env", choices=ENVS, default=None)

    evals = add("evals", None, help="evals")
    esub = evals.add_subparsers(dest="evals_command", metavar="<sub>", required=True)
    p = esub.add_parser("run", parents=[parent], help="evals/run.py を実行する")
    p.set_defaults(func=cmd_evals_run)
    p.add_argument("--dry-run", action="store_true")
    return root


def main(argv: list[str] | None = None) -> int:
    _utf8_stdio()
    argv = list(sys.argv[1:] if argv is None else argv)
    leading = 0
    while leading < len(argv):
        if argv[leading] in ("--home", "--sid"):
            leading += 2
        elif argv[leading] == "--json":
            leading += 1
        else:
            break
    if leading < len(argv) and argv[leading] == "hook":
        return _hook_main(argv)
    try:
        args = build_parser().parse_args(argv)  # every subparsers action is required, so args.func is set
        with _using_home(args):
            return int(args.func(args) or 0)
    except UserError as e:
        _err(str(e))
        return 1
    except SystemExit as e:  # --help
        code = e.code
        return code if isinstance(code, int) else (0 if code is None else 1)
    except KeyboardInterrupt:
        return 130
    except Exception as e:  # noqa: BLE001
        _err(f"内部エラー: {type(e).__name__}: {e}")
        return 2


# ---------------------------------------------------------------- moved names
# Command handlers and their helpers moved out of this file on 2026-10-19. `core.ctx.cli.<name>` keeps
# resolving them (installer, tests, customer code) until 0.2.0 (docs/DECISIONS.md). Only names defined
# in those modules are served, not what they import.
_MOVED_TO = (cli_common, cmd_task, cmd_memory, cmd_persona, cmd_admin)


def __getattr__(name: str):
    for module in _MOVED_TO:
        value = module.__dict__.get(name)
        if value is None or isinstance(value, types.ModuleType):
            continue
        if getattr(value, "__module__", module.__name__) == module.__name__:
            return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


if __name__ == "__main__":
    sys.exit(main())
