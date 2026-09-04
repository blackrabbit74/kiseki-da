"""search.py — BM25 + time decay + provenance over events / tasks / profile (INTERFACES.md §7).

`search()` only ranks documents and writes the `search` event; the CLI prints the hits
(`[<kind>] <date> <source>(<id>) [stale]` followed by the snippet). Depends on store and taskcard only.
"""
from __future__ import annotations

import datetime as _dt
import math
import re
from collections import Counter
from dataclasses import dataclass

from core.ctx import store as _store
from core.ctx import taskcard
from core.ctx.store import Store, UserError

K1 = 1.5
B = 0.75
HALF_LIFE_DAYS = 90.0
KIND_WEIGHTS = {"profile": 1.0, "tasks": 1.0, "capture": 0.9, "events": 0.7}
CORRECTION_BOOST = 1.2
SNIPPET_TOKENS = 300
KINDS = ("events", "tasks", "profile", "capture")
EVENT_TEXT_TYPES = ("question", "assumption", "worker_return", "proposal")
ELLIPSIS = "…"

# Applied to lowercased text: an ASCII run of 2+ [a-z0-9_] is one token; a CJK run (hiragana,
# katakana incl. ー, CJK ideographs incl. extension A, halfwidth katakana) becomes character bigrams.
_CJK_RANGES = ((0x3040, 0x309F), (0x30A0, 0x30FF), (0x3400, 0x4DBF), (0x4E00, 0x9FFF), (0xFF66, 0xFF9F))
_TOKEN_RE = re.compile(
    r"(?P<ascii>[a-z0-9_]{2,})"
    + "|(?P<cjk>[" + "".join(f"{chr(a)}-{chr(b)}" for a, b in _CJK_RANGES) + "]+)"
)


@dataclass
class _Doc:
    id: str
    kind: str
    source: str
    date: str                       # YYYY-MM-DD ("" when unknown)
    text: str
    stale: bool = False
    boost: float = 1.0              # CORRECTION_BOOST for correction events
    when: _dt.datetime | None = None  # reference time for decay; None = age 0


# ---------------------------------------------------------------- tokenizer

def tokenize(text: str) -> list[str]:
    """Lowercase; ASCII word runs are single tokens, CJK runs become character bigrams
    (a run of length 1 yields that character); punctuation, spaces and single ASCII letters are ignored."""
    out: list[str] = []
    for m in _TOKEN_RE.finditer(_text(text).lower()):
        run = m.group("ascii")
        if run is not None:
            out.append(run)
            continue
        run = m.group("cjk")
        if len(run) == 1:
            out.append(run)
        else:
            out.extend(run[i:i + 2] for i in range(len(run) - 1))
    return out


# ---------------------------------------------------------------- small helpers

def _text(value) -> str:
    if isinstance(value, str):
        return value
    return "" if value is None else str(value)


def _local(naive: _dt.datetime) -> _dt.datetime | None:
    try:
        return naive.astimezone()
    except (OverflowError, OSError, ValueError):
        return None


def _to_date(value) -> _dt.date | None:
    if isinstance(value, _dt.datetime):
        return value.date()
    if isinstance(value, _dt.date):
        return value
    if isinstance(value, str):
        try:
            return _dt.date.fromisoformat(value.strip()[:10])
        except ValueError:
            return None
    return None


def _to_datetime(value) -> _dt.datetime | None:
    """ts string / date / datetime → aware datetime (naive values are local time); None if unparsable."""
    if isinstance(value, _dt.datetime):
        return value if value.tzinfo is not None else _local(value)
    if isinstance(value, _dt.date):
        return _local(_dt.datetime.combine(value, _dt.time.min))
    if isinstance(value, str):
        parsed = _store.parse_ts(value.strip())
        if parsed is not None:
            return parsed
        day = _to_date(value)
        return None if day is None else _local(_dt.datetime.combine(day, _dt.time.min))
    return None


def _age_days(when: _dt.datetime | None, now: _dt.datetime) -> float:
    if when is None:
        return 0.0
    return max(0.0, (now - when).total_seconds() / 86400.0)


def _strip_log(text: str) -> str:
    """Drop everything from the `# Log` line to the end of a rendered card."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.strip() == "# Log":
            return "\n".join(lines[:i]).rstrip()
    return text


def _snippet(text: str, limit: int = SNIPPET_TOKENS) -> str:
    """Cut `text` so that estimate_tokens(snippet) <= limit, preferring a line / whitespace boundary."""
    text = text.strip()
    if _store.estimate_tokens(text) <= limit:
        return text
    lo, hi = 0, len(text)
    while lo < hi:  # longest prefix such that prefix + ELLIPSIS still fits (the estimate is monotone)
        mid = (lo + hi + 1) // 2
        if _store.estimate_tokens(text[:mid] + ELLIPSIS) <= limit:
            lo = mid
        else:
            hi = mid - 1
    cut = lo
    j = cut - 1
    while j > 0 and not text[j].isspace():
        j -= 1
    head = text[:j] if j >= cut // 2 else text[:cut]  # use the boundary only if it keeps at least half
    head = head.rstrip() or text[:cut].rstrip()
    return head + ELLIPSIS


# ---------------------------------------------------------------- corpus

def _event_docs(store: Store, since_days: int | None, wanted: set[str]) -> list[_Doc]:
    docs: list[_Doc] = []
    for ev in store.iter_events(since_days=since_days):
        t = ev.get("type")
        boost = 1.0
        if t == "capture":
            kind, source, text = "capture", "capture", _text(ev.get("text"))
        elif t == "correction":
            kind, source, boost = "events", "correction", CORRECTION_BOOST
            text = f"{_text(ev.get('before'))} {_text(ev.get('after'))}"
        elif t in EVENT_TEXT_TYPES:
            kind, source, text = "events", str(t), _text(ev.get("text"))
        else:
            continue  # tool_call, task_*, gate, guard, ... are never indexed
        if kind not in wanted:
            continue
        ts = ev.get("ts")
        docs.append(_Doc(id=f"ev:{ev.get('sid')}:{ev.get('seq')}", kind=kind, source=source,
                         date=_text(ts)[:10], text=text, boost=boost, when=_to_datetime(ts)))
    return docs


def _task_docs(store: Store) -> list[_Doc]:
    docs: list[_Doc] = []
    for tid in store.list_tasks():
        try:
            card = taskcard.load(store, tid)
        except (OSError, ValueError, UserError):
            continue  # an unreadable card must not break the whole search
        docs.append(_Doc(id=f"task:{card.id}", kind="tasks", source="task", date=_text(card.updated)[:10],
                         text=_strip_log(taskcard.render(card)), when=_to_datetime(card.updated)))
    return docs


def _profile_docs(store: Store) -> list[_Doc]:
    docs: list[_Doc] = []
    # Project stores expose only common identity/constraints/preferences plus
    # this project's profile.  No other project directory enters the corpus.
    profile = store.read_effective_profile()
    today = _store.today()
    for section in _store.SECTIONS:
        for item in profile.get(section) or []:
            if not isinstance(item, dict):
                continue
            review_by = _to_date(item.get("review_by"))
            recorded = item.get("recorded_at")
            docs.append(_Doc(id=f"profile:{_text(item.get('id'))}", kind="profile",
                             source=_text(item.get("source")), date=_text(recorded)[:10],
                             text=_text(item.get("text")), stale=review_by is not None and review_by < today,
                             when=_to_datetime(recorded)))
    return docs


def _corpus(store: Store, since_days: int | None, wanted: set[str]) -> list[_Doc]:
    docs: list[_Doc] = []
    if wanted & {"events", "capture"}:
        docs.extend(_event_docs(store, since_days, wanted))
    if "tasks" in wanted:
        docs.extend(_task_docs(store))
    if "profile" in wanted:
        docs.extend(_profile_docs(store))
    return docs


# ---------------------------------------------------------------- ranking

def _rank(docs: list[_Doc], terms: list[str], decay: bool) -> list[dict]:
    """BM25 (k1, b, idf = ln(1 + (N - n + 0.5) / (n + 0.5))) × kind weight × decay × correction boost."""
    indexed = [(d, Counter(tokenize(d.text))) for d in docs]
    indexed = [(d, c) for d, c in indexed if c]  # a document without tokens can never match
    if not indexed:
        return []
    n_docs = len(indexed)
    avgdl = sum(sum(c.values()) for _, c in indexed) / n_docs
    idf: dict[str, float] = {}
    for t in terms:
        n = sum(1 for _, c in indexed if t in c)
        idf[t] = math.log(1.0 + (n_docs - n + 0.5) / (n + 0.5))
    now = _dt.datetime.now().astimezone()
    hits: list[dict] = []
    for d, c in indexed:
        dl = sum(c.values())
        bm25 = 0.0
        for t in terms:
            tf = c.get(t, 0)
            if tf:
                bm25 += idf[t] * tf * (K1 + 1.0) / (tf + K1 * (1.0 - B + B * dl / avgdl))
        if bm25 <= 0.0:
            continue  # contains no query token
        score = bm25 * KIND_WEIGHTS.get(d.kind, 1.0) * d.boost
        if decay:
            score *= 0.5 ** (_age_days(d.when, now) / HALF_LIFE_DAYS)
        score = round(score, 4)
        if score <= 0.0:
            continue
        hits.append({"id": d.id, "kind": d.kind, "date": d.date, "source": d.source, "stale": bool(d.stale),
                     "score": float(score), "snippet": _snippet(d.text)})
    hits.sort(key=lambda h: h["id"])                                   # final tie-break: id ascending
    hits.sort(key=lambda h: (h["score"], h["date"]), reverse=True)     # score desc, then date desc (stable)
    return hits


def search(store: Store, query: str, k: int = 5, since_days: int = 180,
           kinds: list[str] | None = None, decay: bool = True) -> list[dict]:
    """Return ≤k hits {"id","kind","date","source","stale","score","snippet"} and write the `search` event.

    `since_days` applies to events (kinds events / capture) only; tasks and profile are always indexed.
    """
    query = _text(query)
    if isinstance(kinds, str):
        kinds = [kinds]
    wanted = set(KINDS) if not kinds else {str(x) for x in kinds}
    terms = list(dict.fromkeys(tokenize(query)))  # unique query tokens, first-seen order
    hits: list[dict] = []
    if terms:
        hits = _rank(_corpus(store, since_days, wanted), terms, decay)[:max(int(k), 0)]
    store.append_event({"type": "search", "query": query, "k": k, "hits": [h["id"] for h in hits]})
    return hits
