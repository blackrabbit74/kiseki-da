"""cmd_memory.py — `search`, `context`, `capture`, `candidate …`, `approve`, `reject` and `remember`.

Heavier modules (search, build, evidence) are imported lazily inside the commands, as before the split.
"""
from __future__ import annotations

import json
import re
import sys

from core.ctx import store as _store
from core.ctx.cli_common import _emit_json, _json, _make_store, _out
from core.ctx.store import UserError


SEARCH_KINDS = ("events", "tasks", "profile", "capture")


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
