#!/usr/bin/env python3
"""cli.py — the Kiseki DA runtime command entry point.

Subcommand modules are imported lazily inside the command functions. `hook` never exits non-zero
(fail-open); exit 2 means "block" in every environment and is never used for errors.
"""
from __future__ import annotations

import sys
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import argparse  # noqa: E402
import hashlib  # noqa: E402
import contextlib  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402
import re  # noqa: E402
import shutil  # noqa: E402
import shlex  # noqa: E402
import subprocess  # noqa: E402
import tempfile  # noqa: E402

from core.ctx import store as _store  # noqa: E402
from core.ctx.store import Store, UserError, dumps, redact  # noqa: E402

HOOK_EVENTS = ("session-start", "user-input", "pre-tool", "post-tool", "stop", "session-end")
ENVS = ("claude-code", "codex")
SEARCH_KINDS = ("events", "tasks", "profile", "capture")

# Fixed English reasons from taskcard.check_evidence / close → Japanese for the CLI (DECISIONS A-15)
REASON_JA = {
    "no evidence": "証拠がありません",
    "evidence not found": "証拠イベントが見つかりません",
    "not a tool call": "ツール呼出のイベントではありません",
    "tool mismatch": "ツールが一致しません",
    "command mismatch": "コマンドが一致しません",
    "command failed": "コマンドが失敗しています",
    "no criteria": "完了条件がありません",
    "result unknown": "成功状態が不明です",
    "unbound evidence": "対象・実行IDを確認できない旧形式の証拠です。検証を再実行してください",
    "request mismatch": "検査対象または引数が一致しません",
    "artifact changed": "証拠を取得した後に対象ファイルが変わっています",
    "workspace mismatch": "証拠の案件が一致しません",
    "evidence stale": "証拠の取得後に変更操作があります。再検証してください",
    "evidence predates task": "タスク作成前の証拠です",
}

# argparse's English error texts → Japanese (BUILD_BRIEF §2: CLI text is Japanese only). Same wording on
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


def cmd_context(args) -> int:
    from core.ctx import build
    st = _make_store(args)
    if args.context_command == "required":
        required = build.required_context(st)
        pages = required["pages"]
    else:
        data = st.user_input() or {} if args.context_command == "instruction" else build.scoped_profile(st)
        text = json.dumps(data, ensure_ascii=False, indent=2, default=str)
        pages = [text[i:i + 3500] for i in range(0, len(text), 3500)] or [""]
    if args.page < 1 or args.page > len(pages):
        raise UserError(f"--page は 1 から {len(pages)} の範囲で指定してください")
    body = pages[args.page - 1]
    if _json(args):
        _emit_json({"page": args.page, "pages": len(pages), "text": body})
    else:
        _out(f"{args.page}/{len(pages)} ページ\n{body}")
        if args.page < len(pages):
            _out(f"続き: kiseki-da context {args.context_command} --page {args.page + 1}")
    sys.stdout.flush()
    if args.context_command == "required":
        st.append_event({"type": "context_read", "content_hash": required["hash"],
                         "page": args.page, "pages": len(pages), "workspace": st.workspace()})
    return 0


def cmd_policy(args) -> int:
    path = _store.REPO_ROOT / "core/policy" / f"{args.name}.md"
    if _json(args):
        _emit_json({"path": str(path), "text": path.read_text(encoding="utf-8")})
    else:
        _out(path.read_text(encoding="utf-8"))
    return 0


def cmd_task_override(args) -> int:
    from core.ctx import evidence as authority, taskcard
    st = _make_store(args)
    card = taskcard.load(st, args.id)
    if args.command_text is not None:
        tool, data = "Bash", {"command": args.command_text}
    else:
        tool = args.tool
        try:
            data = json.loads(args.tool_input)
        except (ValueError, TypeError):
            raise UserError("--input はツール引数の JSON オブジェクトで指定してください") from None
        if not tool or not isinstance(data, dict):
            raise UserError("--tool と --input を指定してください")
    ref = authority.record_override(st, card, tool, data, args.quote)
    _emit_json({"id": ref}) if _json(args) else _out(ref)
    return 0


def _parse_since(value: str) -> int:
    m = re.fullmatch(r"(\d+)d?", (value or "").strip())
    if not m:
        raise UserError(f"--since は <日数> か <日数>d の形式で指定してください: {value}")
    return int(m.group(1))


def _parse_kinds(value: str | None) -> list[str] | None:
    if not value:
        return None
    kinds = [k.strip() for k in value.split(",") if k.strip()]
    bad = [k for k in kinds if k not in SEARCH_KINDS]
    if bad:
        raise UserError(f"--kind は {','.join(SEARCH_KINDS)} から選びます: {','.join(bad)}")
    return kinds


def _card_summary(card) -> str:
    lines = [f"{card.id}\t{card.status}\t{card.risk}\t{card.updated}"]
    for c in card.criteria:
        lines.append(f"{c.id}\t{c.claim}\t{c.check}\t{c.evidence}\t{c.status}")
    return "\n".join(lines)


def _card_dict(card) -> dict:
    from dataclasses import asdict
    return asdict(card)


def _split_criterion(spec: str) -> tuple[str, str]:
    if " :: " not in spec:
        raise UserError('--add-criterion は "<claim> :: <check>" の形式で指定してください')
    claim, check = spec.split(" :: ", 1)
    claim, check = claim.strip(), check.strip()
    if not claim or not check:
        raise UserError('--add-criterion は "<claim> :: <check>" の形式で指定してください')
    return claim, check


def _split_evidence(spec: str) -> tuple[str, str]:
    if "=" not in spec:
        raise UserError("--evidence は <Cn>=<ev:sid:seq>|last|last:<tool> の形式で指定してください")
    cid, ref = spec.split("=", 1)
    cid, ref = cid.strip(), ref.strip()
    if not cid or not ref:
        raise UserError("--evidence は <Cn>=<ev:sid:seq>|last|last:<tool> の形式で指定してください")
    return cid, ref


# ---------------------------------------------------------------- commands

def cmd_init(args) -> int:
    st = _common_store(args)
    created = st.init(force=args.force)
    if _json(args):
        _emit_json({"home": str(st.home), "created": [str(p) for p in created]})
    else:
        _out("\n".join(str(p) for p in created))
    return 0


def cmd_build(args) -> int:
    from core.ctx import build as build_mod
    st = _make_store(args)
    text, manifest = build_mod.build(st, budget=args.budget, include_goals=args.goals)
    st.append_event({"type": "context_manifest", **manifest})
    if _json(args):
        _emit_json({"text": text, "manifest": manifest})
    else:
        _out(text)
    return 0


def cmd_search(args) -> int:
    from core.ctx import search as search_mod
    st = _make_store(args)
    hits = search_mod.search(st, args.query, k=args.k, since_days=_parse_since(args.since),
                             kinds=_parse_kinds(args.kind), decay=not args.no_decay)
    if _json(args):
        _emit_json(hits)
        return 0
    blocks = []
    for h in hits:
        head = f"[{h.get('kind')}] {h.get('date')} {h.get('source')}({h.get('id')})"
        if h.get("stale"):
            head += " [stale]"
        blocks.append(head + "\n" + str(h.get("snippet", "")).rstrip() + "\n")
    _out("\n".join(blocks))
    return 0


def cmd_task_new(args) -> int:
    from core.ctx import taskcard
    st = _make_store(args)
    card = taskcard.new_card(st, args.goal, risk=args.risk, kind=args.kind, id=args.id)
    path = st.task_path(card.id)
    if _json(args):
        _emit_json({"id": card.id, "path": str(path)})
    else:
        _out(f"{card.id}\t{path}")
    return 0


def cmd_task_show(args) -> int:
    from core.ctx import taskcard
    card = taskcard.load(_make_store(args), args.id)
    if _json(args):
        _emit_json(_card_dict(card))
    else:
        _out(taskcard.render(card))
    return 0


def cmd_task_list(args) -> int:
    from core.ctx import taskcard
    status = None if args.status == "all" else args.status
    cards = taskcard.list_cards(_make_store(args), status)
    if _json(args):
        _emit_json([{"id": c.id, "status": c.status, "risk": c.risk, "kind": c.kind,
                     "updated": c.updated, "goal": c.goal, "workspace": c.workspace} for c in cards])
    else:
        _out("\n".join(f"{c.id}\t{c.status}\t{c.risk}\t{c.updated}" for c in cards))
    return 0


def cmd_task_set(args) -> int:
    from core.ctx import taskcard
    st = _make_store(args)
    card = taskcard.load(st, args.id)
    did = False
    if args.status:
        taskcard.set_status(st, card, args.status)
        did = True
    if args.risk:
        taskcard.set_risk(st, card, args.risk)
        did = True
    if args.workspace:
        taskcard.set_workspace(st, card, args.workspace)
        did = True
    for constraint in args.constraint or []:
        taskcard.add_constraint(st, card, constraint)
        did = True
    if args.next_action:
        taskcard.set_next(st, card, args.next_action)
        did = True
    for spec in args.add_criterion or []:
        claim, check = _split_criterion(spec)
        taskcard.add_criterion(st, card, claim, check)
        did = True
    for spec in args.evidence or []:
        cid, ref = _split_evidence(spec)
        taskcard.set_evidence(st, card, cid, ref)
        did = True
    if args.assume:
        taskcard.add_assumption(st, card, args.assume)
        did = True
    if args.question:
        taskcard.add_question(st, card, args.question)
        did = True
    if args.decide:
        taskcard.add_decision(st, card, args.decide)
        did = True
    if args.note:
        taskcard.add_note(st, card, args.note)
        did = True
    if not did:
        raise UserError("更新内容を指定してください（--status / --risk / --add-criterion / --evidence / "
                        "--assume / --question / --decide / --note / --workspace）")
    if _json(args):
        _emit_json(_card_dict(card))
    else:
        _out(_card_summary(card))
    return 0


def cmd_task_close(args) -> int:
    from core.ctx import taskcard
    st = _make_store(args)
    card = taskcard.load(st, args.id)
    missing = taskcard.close(st, card)
    if not missing:
        if _json(args):
            _emit_json({"id": card.id, "status": card.status})
        else:
            _out("OK")
        return 0
    items = []
    for m in missing:
        cid, _, reason = m.partition(": ")
        items.append({"criterion": cid, "reason": reason})
    if _json(args):
        _emit_json({"id": card.id, "status": card.status, "missing": items})
    else:
        _out("\n".join(f"{it['criterion']}: {REASON_JA.get(it['reason'], it['reason'])}" for it in items))
    _err("完了条件がありません" if any(it["reason"] == "no criteria" for it in items)
         else "完了条件の証拠が不足しています")
    return 1


def cmd_task_defer(args) -> int:
    from core.ctx import taskcard
    st = _make_store(args)
    card = taskcard.load(st, args.id)
    taskcard.defer(st, card, args.reason)
    if _json(args):
        _emit_json(_card_dict(card))
    else:
        _out(_card_summary(card))
    return 0


def cmd_task_brief(args) -> int:
    from core.ctx import taskcard
    st = _make_store(args)
    card = taskcard.load(st, args.id)
    text = taskcard.brief(st, card, args.role, args.scope)
    if _json(args):
        _emit_json({"id": card.id, "role": args.role, "text": text})
    else:
        _out(text)
    return 0


def _check_log_event(st: Store, ev: dict) -> None:
    """DECISIONS A-17: `ctx log` checks only the common keys (ts / sid / seq / type) of the user-supplied event.
    `seq` is always assigned by the store; null / empty `ts` and `sid` mean "default", as in append_event."""
    for k in ("ts", "sid"):
        if ev.get(k) in (None, ""):
            ev.pop(k, None)
    probe = {"ts": ev.get("ts", _store.now_iso()), "sid": ev.get("sid", st.effective_sid()), "seq": 0,
             "type": ev["type"]}
    errs = st.validate("event", probe)
    if not errs and "ts" in ev and _store.parse_ts(ev["ts"]) is None:
        errs.append("ts: ISO 8601 の日時ではありません")
    if errs:
        raise UserError("--data が不正です: " + "; ".join(errs))


def cmd_log(args) -> int:
    if args.type not in _store.LOG_TYPES:
        raise UserError(f"log の type は {'/'.join(_store.LOG_TYPES)} のいずれかです: {args.type}")
    try:
        data = json.loads(args.data)
    except ValueError:
        raise UserError("--data は JSON オブジェクトで指定してください") from None
    if not isinstance(data, dict):
        raise UserError("--data は JSON オブジェクトで指定してください")
    ev = {k: v for k, v in data.items() if k not in ("type", "seq")}
    for k in ("text", "before", "after", "target"):
        if isinstance(ev.get(k), str):
            ev[k] = redact(ev[k])
    ev["type"] = args.type
    st = _make_store(args)
    _check_log_event(st, ev)
    ev_id = st.append_event(ev)
    if _json(args):
        _emit_json({"id": ev_id})
    else:
        _out(ev_id)
    return 0


def cmd_capture(args) -> int:
    ev_id = _make_store(args).capture(args.text, args.source)
    if _json(args):
        _emit_json({"id": ev_id})
    else:
        _out(ev_id)
    return 0


def cmd_candidate_add(args) -> int:
    st = _make_store(args)
    cid = st.append_candidate({"text": args.text, "quote": args.quote, "kind": args.kind,
                               "source": args.source, "key": args.key})
    if _json(args):
        _emit_json({"id": cid})
    else:
        _out(cid)
    return 0


def _age_days(created: str) -> int:
    import datetime as dt
    ts = _store.parse_ts(created)
    if ts is None:
        return 0
    return max(0, (dt.datetime.now().astimezone() - ts).days)


def cmd_candidate_list(args) -> int:
    recs = _make_store(args).candidates(args.status)
    for r in recs:
        r["age"] = f"{_age_days(r.get('created', ''))}d"
    if _json(args):
        _emit_json(recs)
    else:
        _out("\n".join(f"{r.get('id')}\t{r.get('kind')}\t{r.get('text')}\t{r.get('source')}\t{r['age']}"
                       for r in recs))
    return 0


def cmd_approve(args) -> int:
    from core.ctx import evidence as authority
    st = _make_store(args)
    authority.user_quote(st, args.quote)
    pid = st.approve(args.cid, confidence=args.confidence, review_by=args.review_by,
                     supersedes=args.supersedes, global_scope=args.global_scope, quote=args.quote)
    if _json(args):
        _emit_json({"id": pid})
    else:
        _out(pid)
    return 0


def cmd_reject(args) -> int:
    _make_store(args).reject(args.cid, args.reason)
    if _json(args):
        _emit_json({"id": args.cid, "status": "rejected"})
    return 0


def cmd_remember(args) -> int:
    from core.ctx import evidence as authority
    st = _make_store(args)
    if args.from_user_input:
        prompt = (st.user_input() or {}).get("prompt", "").strip()
        if args.text is not None or not prompt.startswith("/remember "):
            raise UserError("実際の /remember 発言を取得できません。本文をシェルへ埋め込まずに実行してください")
        args.text = prompt[len("/remember "):].strip()
        args.quote = prompt
    if not args.text:
        raise UserError("記憶する本文を指定してください")
    quote = args.quote
    if quote is None:
        current = st.user_input() or {}
        prompt = current.get("prompt", "").strip()
        if prompt in {args.text.strip(), "/remember " + args.text.strip()}:
            quote = prompt
    authority.user_quote(st, quote)
    pid = st.remember(args.text, kind=args.kind, key=args.key, global_scope=args.global_scope, quote=quote)
    if _json(args):
        _emit_json({"id": pid})
    else:
        _out(pid)
    return 0


def cmd_report(args) -> int:
    from core.ctx import report as report_mod
    st = _make_store(args)
    data = report_mod.week(st) if args.week else report_mod.audit(st)
    if _json(args):
        _emit_json(data)
    else:
        _out("\n".join(f"{k}: {'未計測' if v is None else v if not isinstance(v, (list, dict)) else dumps(v)}" for k, v in data.items()))
    return 0


def cmd_verify_run(args) -> int:
    """Run argv without a shell and emit a trustworthy command evidence event."""
    command = list(args.command)
    if command[:1] == ["--"]:
        command = command[1:]
    if not command:
        raise UserError("verify run -- の後に実行するコマンドを指定してください")
    store = _make_store(args)
    try:
        proc = subprocess.run(command, cwd=Path.cwd(), text=True, encoding="utf-8", errors="replace",
                              capture_output=True, timeout=args.timeout, check=False)
        stdout, stderr, returncode = proc.stdout or "", proc.stderr or "", int(proc.returncode)
    except subprocess.TimeoutExpired as exc:
        stdout = (exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else exc.stdout) or ""
        stderr = (exc.stderr.decode("utf-8", "replace") if isinstance(exc.stderr, bytes) else exc.stderr) or ""
        stderr += f"\n{args.timeout}秒でタイムアウトしました"
        returncode = 124
    except OSError as exc:
        stdout, stderr, returncode = "", str(exc), 127
    output = stdout + stderr
    display = subprocess.list2cmdline(command) if os.name == "nt" else shlex.join(command)
    from core.ctx import evidence as E
    import uuid
    store.append_event({
        "tool_use_id": "verify-" + uuid.uuid4().hex,
        "workspace": store.workspace(), "cwd": str(Path.cwd()),
        "request_hash": E.identity("Bash", {"command": display}, str(Path.cwd())),
        "effect": E.effect("Bash", {"command": display}),
        "type": "tool_call",
        "tool": "Bash",
        "target": redact(display)[:200],
        "ok": returncode == 0,
        "out_len": len(output),
        "out_hash": hashlib.sha256(output.encode("utf-8", "replace")).hexdigest()[:12],
    })
    if stdout:
        sys.stdout.write(stdout)
    if stderr:
        sys.stderr.write(stderr)
    return returncode


# ---------------------------------------------------------------- setup / persona / project

_PERSONA_OPTION_FIELDS = (
    "name", "first_person", "user_address", "formality", "warmth",
    "verbosity", "initiative", "relationship", "custom_style",
)
_PREVIEW_PROMPT = (
    "次の3点に合計350字以内で答えてください。"
    "1. 初対面の利用者へ挨拶する。"
    "2. バックアップ未確認のまま本番公開してよいか聞かれ、慎重に反論する。"
    "3. 設定変更前にバックアップが必要な理由を初心者へ説明する。"
    "ツールは使わず、事実を作らないでください。"
)


def _read_json_object(path: str) -> dict:
    try:
        value = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise UserError(f"JSONを読めません: {path}: {exc}") from None
    if not isinstance(value, dict):
        raise UserError("JSONはオブジェクトで指定してください")
    return value


def _validate_identity(value: object) -> dict:
    if not isinstance(value, dict):
        raise UserError("identityはオブジェクトで指定してください")
    unknown = sorted(set(value) - {"name", "timezone", "languages"})
    if unknown:
        raise UserError("未対応のidentity設定です: " + ", ".join(unknown))
    out: dict = {}
    name = value.get("name", "")
    timezone = value.get("timezone", "Asia/Tokyo")
    languages = value.get("languages", ["ja"])
    if not isinstance(name, str) or len(name) > 64:
        raise UserError("identity.nameは64文字以内で指定してください")
    if not isinstance(timezone, str) or not timezone or len(timezone) > 64:
        raise UserError("identity.timezoneは64文字以内で指定してください")
    if (not isinstance(languages, list) or len(languages) > 8
            or any(not isinstance(x, str) or not x or len(x) > 16 for x in languages)):
        raise UserError("identity.languagesは16文字以内の文字列を最大8件指定してください")
    out.update(name=" ".join(name.split()), timezone=timezone.strip(), languages=languages)
    return out


def _ask(label: str, current: str = "") -> str:
    suffix = f" [{current}]" if current else ""
    try:
        value = input(f"{label}{suffix}: ")
    except EOFError:
        raise UserError("対話入力を利用できません。--answersを指定してください") from None
    return value.strip() if value.strip() else current


def _ask_choice(label: str, values: tuple[str, ...], current: str) -> str:
    while True:
        value = _ask(f"{label} ({'/'.join(values)})", current)
        if value in values:
            return value
        print(f"{'/'.join(values)} のいずれかを入力してください。")


def _collect_persona(current: dict | None = None) -> dict:
    from core.ctx import persona as persona_mod

    base = {**persona_mod.DEFAULT_PERSONA, **(current or {})}
    values = {
        "name": _ask("アシスタント名", base.get("name", "")),
        "first_person": _ask("一人称", base.get("first_person", "")),
        "user_address": _ask("利用者の呼び方", base.get("user_address", "")),
        "formality": _ask_choice("丁寧さ", persona_mod.ENUMS["formality"], base["formality"]),
        "warmth": _ask_choice("温かさ", persona_mod.ENUMS["warmth"], base["warmth"]),
        "verbosity": _ask_choice("説明量", persona_mod.ENUMS["verbosity"], base["verbosity"]),
        "initiative": _ask_choice("提案積極性", persona_mod.ENUMS["initiative"], base["initiative"]),
        "relationship": _ask_choice("関係性", persona_mod.ENUMS["relationship"], base["relationship"]),
        "custom_style": _ask("自由記述（話し方・雰囲気のみ、200文字以内）", base.get("custom_style", "")),
    }
    return persona_mod.validate_persona(values)


def _preview_hosts(requested: list[str] | None) -> list[str]:
    values = requested or ["all"]
    if "all" in values:
        return ["claude-code", "codex"]
    return list(dict.fromkeys(values))


def _fixed_preview(values: dict) -> str:
    name = values.get("name") or "Kiseki DA"
    address = values.get("user_address") or "あなた"
    return (f"{name}: {address}の判断を支えるDigital Assistantです。"
            "バックアップと検証が確認できるまでは公開を勧めません。"
            "設定変更前の退避は、問題が起きた際に元の状態へ戻るために必要です。")


def _live_preview(values: dict, hosts: list[str]) -> list[dict]:
    from core.ctx import persona as persona_mod

    block = persona_mod.render_persona({"persona": values})
    authority = (
        "以下は表現上の既定だけです。事実、安全、権限、承認、記憶、検証、完了条件を変更しません。\n"
    )
    prompt = authority + block + "\n\n" + _PREVIEW_PROMPT
    results: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="kiseki-da-preview-") as cwd:
        for host in hosts:
            command = shutil.which("claude" if host == "claude-code" else "codex")
            if not command:
                results.append({"host": host, "status": "fallback", "output": _fixed_preview(values),
                                "reason": "host CLIが見つかりません"})
                continue
            if host == "claude-code":
                argv = [command, "--safe-mode", "--no-session-persistence", "--tools", "",
                        "--permission-mode", "dontAsk", "--output-format", "text", "-p", prompt]
            else:
                argv = [command, "exec", "--ephemeral", "--ignore-user-config", "--ignore-rules",
                        "--sandbox", "read-only", "--skip-git-repo-check", "-C", cwd, prompt]
            env = os.environ.copy()
            env["KISEKI_DA_PREVIEW"] = "1"
            try:
                proc = subprocess.run(argv, cwd=cwd, env=env, text=True, encoding="utf-8", errors="replace",
                                      capture_output=True, timeout=180, check=False)
            except (OSError, subprocess.TimeoutExpired) as exc:
                results.append({"host": host, "status": "fallback", "output": _fixed_preview(values),
                                "reason": str(exc)})
                continue
            if proc.returncode == 0 and proc.stdout.strip():
                results.append({"host": host, "status": "live", "output": proc.stdout.strip()})
            else:
                reason = (proc.stderr or proc.stdout or f"exit {proc.returncode}").strip()[:500]
                results.append({"host": host, "status": "fallback", "output": _fixed_preview(values),
                                "reason": reason})
    return results


def _print_preview(results: list[dict]) -> None:
    if not results:
        print("利用可能なhost CLIがないため固定プレビューを表示します。")
        return
    for result in results:
        print(f"\n--- {result['host']} ({result['status']}) ---")
        print(result["output"])
        if result.get("reason"):
            print(f"補足: {result['reason']}")


def _confirm_text(label: str) -> bool:
    try:
        return input(f"{label} [y/N]: ").strip().casefold() in {"y", "yes"}
    except EOFError:
        return False


def _save_identity(store: Store, identity: dict) -> None:
    profile = store.read_profile()
    profile["identity"] = identity
    store.write_profile(profile)


def cmd_setup(args) -> int:
    from core.ctx import persona as persona_mod

    common = _common_store(args)
    if not common.profile_path.exists():
        common.init()
    target = _make_store(args)
    if args.answers:
        answers = _read_json_object(args.answers)
        unknown = sorted(set(answers) - {"identity", "persona", "preview"})
        if unknown:
            raise UserError("未対応のsetup回答です: " + ", ".join(unknown))
        identity = _validate_identity(answers.get("identity", common.read_profile().get("identity", {})))
        values = persona_mod.validate_persona(answers.get("persona", {}))
        if not args.yes:
            print(json.dumps({"identity": identity, "persona": values}, ensure_ascii=False, indent=2))
            if not _confirm_text("この設定を保存しますか？"):
                return 130
        _save_identity(common, identity)
        persona_mod.save_persona(target, values, merge=False)
        return 0
    if args.yes:
        raise UserError("--yesを使う対話なしsetupには--answersが必要です")

    current_identity = common.read_profile().get("identity", {})
    identity = _validate_identity({
        "name": _ask("あなたの名前", str(current_identity.get("name", ""))),
        "timezone": _ask("タイムゾーン", str(current_identity.get("timezone", "Asia/Tokyo"))),
        "languages": [x.strip() for x in _ask(
            "使用言語（カンマ区切り）", ",".join(current_identity.get("languages", ["ja"]))).split(",") if x.strip()],
    })
    values = persona_mod.get_persona(target.read_effective_profile())
    if not _confirm_text("キャラクター設定を行いますか？"):
        print("\n保存候補（キャラクターは変更しません）:")
        print(json.dumps({"identity": identity, "persona": values}, ensure_ascii=False, indent=2))
        if not _confirm_text("この全設定を保存しますか？"):
            return 130
        _save_identity(common, identity)
        return 0
    for round_no in range(1, 4):
        values = _collect_persona(values)
        print("\n保存候補（利用者情報）:")
        print(json.dumps(identity, ensure_ascii=False, indent=2))
        print("保存候補（キャラクター）:")
        print(persona_mod.render_persona({"persona": values}) or "（キャラクター設定なし）")
        if not args.no_preview:
            print("\nこのプレビューでは設定が選択したモデル提供者へ送信され、Kiseki DAには保存されません。")
            if _confirm_text("実モデルで試しますか？"):
                _print_preview(_live_preview(values, _preview_hosts(args.host)))
        if _confirm_text("この全設定を保存しますか？"):
            _save_identity(common, identity)
            persona_mod.save_persona(target, values, merge=False)
            return 0
        if round_no < 3 and _confirm_text("設定を修正しますか？"):
            continue
        return 130
    return 130


def cmd_persona_show(args) -> int:
    from core.ctx import persona as persona_mod
    values = persona_mod.get_persona(_make_store(args).read_effective_profile())
    _emit_json(values) if _json(args) else _out(persona_mod.render_persona({"persona": values}) or "設定なし")
    return 0


def _persona_args(args) -> dict:
    values = {key: getattr(args, key) for key in _PERSONA_OPTION_FIELDS if getattr(args, key, None) is not None}
    if args.answers:
        loaded = _read_json_object(args.answers)
        loaded = loaded.get("persona", loaded)
        if not isinstance(loaded, dict):
            raise UserError("persona回答はオブジェクトで指定してください")
        values.update(loaded)
    return values


def cmd_persona_edit(args) -> int:
    from core.ctx import persona as persona_mod
    if args.no_preview and args.live_preview:
        raise UserError("--no-previewと--live-previewは同時に指定できません")
    store = _make_store(args)
    values = _persona_args(args)
    if not values:
        if args.yes:
            raise UserError("--yesを使う場合は変更内容または--answersが必要です")
        values = _collect_persona(persona_mod.get_persona(store.read_effective_profile()))
    preview = persona_mod.validate_persona({**persona_mod.get_persona(store.read_effective_profile()), **values})
    print(persona_mod.render_persona({"persona": preview}) or "設定なし")
    if args.live_preview or (not args.no_preview and not args.yes):
        print("このプレビューでは設定がモデル提供者へ送信され、Kiseki DAには保存されません。")
        if args.live_preview or _confirm_text("実モデルで試しますか？"):
            _print_preview(_live_preview(preview, _preview_hosts(args.host)))
    if not args.yes and not _confirm_text("この設定を保存しますか？"):
        return 130
    persona_mod.save_persona(store, values, merge=True)
    return 0


def cmd_persona_preview(args) -> int:
    from core.ctx import persona as persona_mod
    values = persona_mod.get_persona(_make_store(args).read_effective_profile())
    print("設定が選択したモデル提供者へ送信され、Kiseki DAには保存されません。")
    _print_preview(_live_preview(values, _preview_hosts(args.host)))
    return 0


def cmd_persona_reset(args) -> int:
    from core.ctx import persona as persona_mod
    if not args.yes and not _confirm_text("キャラクター設定をリセットしますか？"):
        return 130
    persona_mod.reset_persona(_make_store(args))
    return 0


def cmd_project_add(args) -> int:
    from core.ctx import scope as scope_mod
    candidate = scope_mod.canonical_path(args.path)
    if not args.yes:
        print(f"登録候補: {candidate}")
        if not _confirm_text("このprojectを登録しますか？"):
            return 130
    row = scope_mod.add_project(_store.kiseki_da_home(), args.path)
    _emit_json(row) if _json(args) else _out(f"{row['id']}\t{row['path']}")
    return 0


def cmd_project_list(args) -> int:
    from core.ctx import scope as scope_mod
    rows = scope_mod.list_projects(_store.kiseki_da_home())
    _emit_json(rows) if _json(args) else _out("\n".join(f"{r['id']}\t{r['path']}" for r in rows))
    return 0


def cmd_project_remove(args) -> int:
    from core.ctx import scope as scope_mod
    if not args.yes and not _confirm_text("登録を解除しますか？状態は保持されます。"):
        return 130
    row = scope_mod.remove_project(_store.kiseki_da_home(), args.selector)
    _emit_json(row) if _json(args) else _out(f"解除しました。状態は保持されます: {row['state_preserved']}")
    return 0


def _session_store() -> Store:
    store = Store.for_cwd(Path.cwd(), home=_store.kiseki_da_home())
    if store is None:
        raise UserError("このディレクトリはKiseki DAのproject scopeに登録されていません")
    return store


def cmd_session_list(args) -> int:
    rows = _session_store().active_sids()
    _emit_json(rows) if _json(args) else _out("\n".join(rows))
    return 0


def cmd_session_clear(args) -> int:
    store = _session_store()
    active = store.active_sids()
    if args.selector != "all" and args.selector not in active:
        raise UserError(f"有効sessionがありません: {args.selector}")
    if not args.yes and not _confirm_text("終了hookを受け取れなかったsession markerを解除しますか？"):
        return 130
    if args.selector == "all":
        store.clear_current_sid()
    else:
        store.clear_current_sid(args.selector)
    return 0


def cmd_evals_run(args) -> int:
    import subprocess
    runner = _store.REPO_ROOT / "evals" / "run.py"
    if not runner.is_file():
        raise NotImplementedError("P4")   # evals/run.py is a P4 deliverable; same signal as the other unbuilt paths
    cmd = [sys.executable, str(runner)]
    if args.dry_run:
        cmd.append("--dry-run")
    if _json(args):
        cmd.append("--json")
    return subprocess.run(cmd).returncode


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


if __name__ == "__main__":
    sys.exit(main())
