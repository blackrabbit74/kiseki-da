"""report.py — weekly metrics (`week`) and quarterly audit (`audit`) over events.jsonl (INTERFACES.md §8).

Both functions are side-effect free: they never write events or state.
"""
from __future__ import annotations

import datetime as _dt
import os
import re
from pathlib import Path

from core.ctx import store as _store
from core.ctx import taskcard
from core.ctx.store import Store

WEEK_DAYS = 7
USEFUL_WINDOW = 10   # events after a question in which an assumption / task_update counts as "useful"
WEEK_KEYS = (
    "sessions", "resident_tokens_avg", "questions", "questions_useful_ratio", "assumptions",
    "corrections", "cards_open", "cards_closed", "evidence_fill_ratio", "gate_blocks", "gate_overrides",
    "guard_deny", "guard_ask", "workers", "candidates_pending", "candidates_approved",
    "candidates_rejected", "stale_items", "searches", "search_cited_ratio",
    "questions_followed_by_update_ratio", "gate_followed_by_defer_ratio", "evidence_reference_ratio",
)

AUDIT_DAYS = 30
AUDIT_KEYS = (
    "file_count", "hooks_never_fired", "event_types_without_writer", "profile_items_never_hit",
    "duplicate_profile_texts", "policy_lines", "policy_tokens",
)
# Normalized hook → the event type it writes on every run (INTERFACES §8), in registration order.
HOOK_EVENT_TYPES = (
    ("session-start", "session_start"), ("user-input", "user_input"), ("pre-tool", "guard"), ("post-tool", "tool_call"),
    ("stop", "gate"), ("session-end", "session_end"),
)
POLICY_PATH = _store.REPO_ROOT / "core" / "policy" / "interaction.md"

# INTERFACES §10 file-count exclusions: root-relative directories, any-depth directory names, root files.
# Same rule as core/tests/test_limits.counted_files; duplicated because core/ctx must not import core.tests.
_EXCLUDED_ROOT_DIRS = frozenset({"build", ".claude", "acceptance", "docs/background"})
_EXCLUDED_DIR_NAMES = frozenset({".git", "__pycache__"})
_EXCLUDED_ROOT_FILES = frozenset({"HANDOFF.md", "BUILD_BRIEF.md", "INTERFACES.md", "PROMPT.md"})
_SKILLS_KEPT = "skills/README.md"


def _ratio(num: int, den: int) -> float:
    return round(num / den, 4) if den else 0.0


def _in_window(ev: dict, cutoff: _dt.datetime) -> bool:
    ts = _store.parse_ts(ev.get("ts"))
    return ts is not None and ts >= cutoff


def _stale_count(profile: dict, today: _dt.date) -> int:
    n = 0
    for section in _store.SECTIONS:
        for item in profile.get(section, []):
            if not isinstance(item, dict):
                continue   # hand-edited `constraints = ["a"]` (list of str) must not abort the report; same guard as build/search
            rb = item.get("review_by")
            try:
                if rb is not None and _store.parse_date(rb) < today:
                    n += 1
            except _store.UserError:
                continue
    return n


def week(store: Store) -> dict:
    """Metrics for the last 7 days (judged by `ts`). Every key of INTERFACES §8 is always present."""
    now = _dt.datetime.now().astimezone()
    cutoff = now - _dt.timedelta(days=WEEK_DAYS)
    events = list(store.iter_events())
    recent = [ev for ev in events if _in_window(ev, cutoff)]

    def count(t: str, **match) -> int:
        return sum(1 for ev in recent if ev.get("type") == t and all(ev.get(k) == v for k, v in match.items()))

    manifests = [ev.get("used") for ev in recent if ev.get("type") == "context_manifest"
                 and isinstance(ev.get("used"), (int, float))]

    # questions_useful_ratio: an assumption or task_update for the same task within the next 10 events
    useful = 0
    questions = 0
    for i, ev in enumerate(events):
        if ev.get("type") != "question" or not _in_window(ev, cutoff):
            continue
        questions += 1
        for later in events[i + 1:i + 1 + USEFUL_WINDOW]:
            if later.get("type") in ("assumption", "task_update") and later.get("task") == ev.get("task"):
                useful += 1
                break

    # gate_overrides: a blocking gate followed (later in the log) by a defer of the same task
    blocks = 0
    overrides = 0
    for i, ev in enumerate(events):
        if ev.get("type") != "gate" or ev.get("blocked") is not True or not _in_window(ev, cutoff):
            continue
        blocks += 1
        for later in events[i + 1:]:
            if (later.get("type") == "task_update" and later.get("task") == ev.get("task")
                    and "defer" in (later.get("changed") or [])):
                overrides += 1
                break

    # evidence_fill_ratio: criteria of R>=1 cards updated within the window
    filled = 0
    referenced = 0
    total = 0
    open_cards = 0
    for cid in store.list_tasks():
        try:
            card = taskcard.load(store, cid)
        except (_store.UserError, OSError, ValueError):
            continue   # one unreadable card (not UTF-8, no permission) must not lose the whole report; same guard as build/search/gate
        if card.status == "open":
            open_cards += 1
        ts = _store.parse_ts(card.updated)
        if card.risk == "R0" or ts is None or ts < cutoff:
            continue
        invalid = {c.id for c, _ in taskcard.missing_evidence(store, card)}
        for c in card.criteria:
            total += 1
            if c.evidence and c.evidence != "-":
                referenced += 1
            if c.id not in invalid:
                filled += 1

    # search_cited_ratio: ev: hits later cited by an evidence.ref of the same sid (lower bound)
    hits_total = 0
    hits_cited = 0
    for i, ev in enumerate(events):
        if ev.get("type") != "search" or not _in_window(ev, cutoff):
            continue
        later_refs = {later.get("ref") for later in events[i + 1:]
                      if later.get("type") == "evidence" and later.get("sid") == ev.get("sid")}
        for hit in ev.get("hits") or []:
            if isinstance(hit, str) and hit.startswith("ev:"):
                hits_total += 1
                if hit in later_refs:
                    hits_cited += 1

    profile = store.read_profile()
    result = {
        "sessions": count("session_start"),
        "resident_tokens_avg": round(sum(manifests) / len(manifests), 1) if manifests else 0.0,
        "questions": questions,
        "questions_useful_ratio": None,  # usefulness requires the user's outcome; an update is not that outcome
        "questions_followed_by_update_ratio": _ratio(useful, questions),
        "assumptions": count("assumption"),
        "corrections": count("correction"),
        "cards_open": open_cards,
        "cards_closed": count("task_close"),
        "evidence_fill_ratio": _ratio(filled, total),
        "evidence_reference_ratio": _ratio(referenced, total),
        "gate_blocks": blocks,
        "gate_overrides": None,
        "gate_followed_by_defer_ratio": _ratio(overrides, blocks),
        "guard_deny": count("guard", decision="deny"),
        "guard_ask": count("guard", decision="ask"),
        "workers": count("worker_dispatch"),
        "candidates_pending": len(store.candidates("pending")),
        # approval{cid: null} is a direct `ctx remember` write, not a candidate (DECISIONS 2026-09-04)
        "candidates_approved": sum(1 for ev in recent if ev.get("type") == "approval"
                                   and ev.get("action") == "approve" and ev.get("cid") is not None),
        "candidates_rejected": count("approval", action="reject"),
        "stale_items": _stale_count(profile, _store.today()),
        "searches": count("search"),
        "search_cited_ratio": None,  # evidence refs are not citations in the final answer
    }
    return {key: result[key] for key in WEEK_KEYS}


def _counted_files() -> list[str]:
    """Repository files counted by INTERFACES §10 (sorted POSIX-relative paths); `.DS_Store` counts (DECISIONS A-3)."""
    root = _store.REPO_ROOT
    out: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        rel = Path(dirpath).relative_to(root).as_posix()
        keep = []
        for d in dirnames:
            child = d if rel == "." else f"{rel}/{d}"
            if d in _EXCLUDED_DIR_NAMES or child in _EXCLUDED_ROOT_DIRS:
                continue
            keep.append(d)
        dirnames[:] = sorted(keep)
        for f in filenames:
            relf = f if rel == "." else f"{rel}/{f}"
            if f.endswith(".pyc") or (rel == "." and f in _EXCLUDED_ROOT_FILES):
                continue
            if (relf == "skills" or relf.startswith("skills/")) and relf != _SKILLS_KEPT:
                continue
            out.append(relf)
    return sorted(out)


def _event_types_without_writer() -> list[str]:
    """EVENT_TYPES with neither a `"type": "<t>"` literal in core/ctx/*.py (read now) nor membership in LOG_TYPES."""
    ctx_dir = _store.REPO_ROOT / "core" / "ctx"
    src = "\n".join(p.read_text(encoding="utf-8") for p in sorted(ctx_dir.glob("*.py")))
    return sorted(t for t in _store.EVENT_TYPES if t not in _store.LOG_TYPES
                  and not re.search(r'"type"\s*:\s*"%s"' % re.escape(t), src))


def _profile_items(profile: dict) -> list[tuple[str, dict]]:
    """(id, item) for every dict item with a str id, in profile order (SECTIONS, then file order).
    Non-dict items and items without a str id are skipped, as in build/search/week."""
    out: list[tuple[str, dict]] = []
    for section in _store.SECTIONS:
        for item in profile.get(section, []):
            if isinstance(item, dict) and isinstance(item.get("id"), str):
                out.append((item["id"], item))
    return out


def audit(store: Store) -> dict:
    """Quarterly audit (INTERFACES §8): structural facts over the repository, the last 30 days of events and
    the profile. Every key of AUDIT_KEYS is always present; reads only (no event, no file)."""
    recent = list(store.iter_events(since_days=AUDIT_DAYS))   # ts unparsable → not counted, as in week()
    fired = {ev.get("type") for ev in recent}
    never_fired = [hook for hook, t in HOOK_EVENT_TYPES if t not in fired]

    hit_ids: set[str] = set()
    for ev in recent:
        if ev.get("type") == "context_manifest":
            hit_ids.update(pid for pid in ev.get("resident_profile_ids", []) if isinstance(pid, str))
        if ev.get("type") != "search":
            continue
        for hit in ev.get("hits") or []:
            if isinstance(hit, str) and hit.startswith("profile:"):
                hit_ids.add(hit.removeprefix("profile:"))

    items = _profile_items(store.read_profile())
    never_hit = sorted({pid for pid, _ in items if pid not in hit_ids})

    by_text: dict[str, list[str]] = {}   # insertion order = first occurrence
    for pid, item in items:
        text = item.get("text")
        if isinstance(text, str):
            by_text.setdefault(text.strip(), []).append(pid)
    duplicates = [{"text": text, "ids": ids} for text, ids in by_text.items() if len(ids) >= 2]

    policy = POLICY_PATH.read_text(encoding="utf-8")   # FileNotFoundError propagates, as in build()
    return {
        "file_count": len(_counted_files()),
        "hooks_never_fired": never_fired,
        "event_types_without_writer": _event_types_without_writer(),
        "profile_items_never_hit": never_hit,
        "duplicate_profile_texts": duplicates,
        "policy_lines": len(policy.splitlines()),
        "policy_tokens": _store.estimate_tokens(policy),
    }
