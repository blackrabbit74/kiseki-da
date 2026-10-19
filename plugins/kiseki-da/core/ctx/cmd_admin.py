"""cmd_admin.py — `init`, `build`, `report`, `policy`, `log`, `project …`, `session …` and `evals run`.

Heavier modules (build, report, scope) are imported lazily inside the commands, as before the split.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from core.ctx import store as _store
from core.ctx.cli_common import _common_store, _confirm_text, _emit_json, _json, _make_store, _out
from core.ctx.store import Store, UserError, dumps, redact


def cmd_policy(args) -> int:
    path = _store.REPO_ROOT / "core/policy" / f"{args.name}.md"
    if _json(args):
        _emit_json({"path": str(path), "text": path.read_text(encoding="utf-8")})
    else:
        _out(path.read_text(encoding="utf-8"))
    return 0


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


def _check_log_event(st: Store, ev: dict) -> None:
    """`ctx log` checks only the common keys (ts / sid / seq / type) of the user-supplied event.
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


def cmd_report(args) -> int:
    from core.ctx import report as report_mod
    st = _make_store(args)
    data = report_mod.week(st) if args.week else report_mod.audit(st)
    if _json(args):
        _emit_json(data)
    else:
        _out("\n".join(f"{k}: {'未計測' if v is None else v if not isinstance(v, (list, dict)) else dumps(v)}" for k, v in data.items()))
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
