"""build.py — bounded resident context and plugin SessionStart policy.

Direct ``build`` calls count but do not render policy for compatibility.  Plugin
SessionStart passes ``include_policy=True`` so the same policy is injected once.
"""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field

from core.ctx import store as _store
from core.ctx import persona as _persona
from core.ctx import taskcard
from core.ctx.store import Store, estimate_tokens

PART_NAMES = ("policy", "constraints", "cards", "persona", "preferences", "goals", "env", "pending")

MAX_CHARS = 9000
LINE_LIMITS = {"constraints": 10, "preferences": 10, "goals": 5}   # A-9
CARD_LIMIT = 2
CARD_TOKENS = 400
ENV_TOKENS = 150
HEADINGS = {
    "constraints": "## 制約",
    "cards": "## 進行中",
    "persona": "## キャラクター（表現上の既定）",
    "preferences": "## 選好",
    "goals": "## 目標",
    "env": "## 環境",
    "pending": "## 未承認",
}
@dataclass
class _Part:
    name: str
    items: list[list[str]] = field(default_factory=list)   # one item = its rendered lines
    always: bool = False                                     # heading printed even when empty
    truncated: bool = False
    item_kinds: list[str] = field(default_factory=list)

    def render(self) -> str:
        if not self.items and not self.always:
            return ""
        lines = [HEADINGS[self.name]]
        for item in self.items:
            lines.extend(item)
        return "\n".join(lines)

    def pop_last(self, kind: str | None = None) -> bool:
        if not self.items:
            return False
        if kind is None:
            self.items.pop()
            if self.item_kinds:
                self.item_kinds.pop()
            self.truncated = True
            return True
        for i in range(len(self.items) - 1, -1, -1):
            if i < len(self.item_kinds) and self.item_kinds[i] == kind:
                self.items.pop(i)
                self.item_kinds.pop(i)
                self.truncated = True
                return True
        return False


# ---------------------------------------------------------------- helpers

def _one_line(value) -> str:
    return " ".join(str(value if value is not None else "").split())


def _as_date(value) -> _dt.date | None:
    """date / datetime / 'YYYY-MM-DD' → date; None when absent or unparsable (such items are never stale)."""
    if value is None or value == "":
        return None
    try:
        return _store.parse_date(value)
    except _store.UserError:
        return None


def _is_stale(item: dict, today: _dt.date) -> bool:
    d = _as_date(item.get("review_by"))
    return d is not None and d < today


def _item_line(item: dict) -> str:
    return f"- {_one_line(item.get('text'))}（{_one_line(item.get('id'))}）"


# ---------------------------------------------------------------- profile parts

def _resolve_keys(items: list[dict], conflicts: list[dict]) -> list[tuple[_dt.date, list[str]]]:
    """Collapse items sharing a `key` (ARCHITECTURE §5.4): only the best source rank survives; two or more
    at the best rank become one ⚠ line plus a conflicts entry. Entries keep profile order and carry the
    newest recorded_at of what they show."""
    groups: dict[str, list[dict]] = {}
    order: list[tuple[str, object]] = []
    for it in items:
        key = _one_line(it.get("key"))
        if key:
            if key not in groups:
                groups[key] = []
                order.append(("key", key))
            groups[key].append(it)
        else:
            order.append(("item", it))
    entries: list[tuple[_dt.date, list[str]]] = []
    for kind, ref in order:
        members = groups[ref] if kind == "key" else [ref]
        best = min(_store.source_rank(m.get("source")) for m in members)
        winners = [m for m in members if _store.source_rank(m.get("source")) == best]
        newest = max(_as_date(w.get("recorded_at")) or _dt.date.min for w in winners)
        if len(winners) == 1:
            entries.append((newest, [_item_line(winners[0])]))
        else:
            conflicts.append({"key": ref, "ids": [_one_line(w.get("id")) for w in winners]})
            joined = " / ".join(f"{_one_line(w.get('text'))}（{_one_line(w.get('id'))}）" for w in winners)
            entries.append((newest, [f"- ⚠ 衝突: {joined}"]))
    return entries


def _profile_part(name: str, items: list, today: _dt.date, conflicts: list[dict],
                  newest_first: bool = False) -> _Part:
    live = [it for it in items if isinstance(it, dict) and not _is_stale(it, today)]
    entries = _resolve_keys(live, conflicts)
    if newest_first:
        entries.sort(key=lambda e: e[0], reverse=True)   # stable: ties keep profile order
    part = _Part(name, [lines for _, lines in entries])
    limit = LINE_LIMITS[name]
    if len(part.items) > limit:
        del part.items[limit:]
        part.truncated = True
    return part


# ---------------------------------------------------------------- cards / env / pending

def _card_lines(card: taskcard.TaskCard) -> list[str]:
    goal = card.goal.strip().splitlines()
    lines = [f"- {card.id} [{card.risk}] {goal[0].strip() if goal else ''}".rstrip()]
    lines.extend(f"  未達: {c.id} {_one_line(c.claim)}" for c in card.criteria if c.status != "pass")
    lines.extend(f"  未確定: {_one_line(q)}" for q in card.questions)
    return lines


def _cards_part(store: Store) -> _Part:
    open_cards: list[taskcard.TaskCard] = []
    for tid in store.list_tasks():
        try:
            card = taskcard.load(store, tid)
        except (OSError, ValueError, _store.UserError):
            continue   # one unreadable card (not UTF-8, no permission) must not empty the whole block; same guard as search
        if card.status == "open":
            open_cards.append(card)
    open_cards.sort(key=lambda c: (c.updated, c.id), reverse=True)   # newest `updated` first, as taskcard.list_cards
    part = _Part("cards", [_card_lines(c) for c in open_cards[:CARD_LIMIT]])
    part.truncated = len(open_cards) > CARD_LIMIT
    while part.items and estimate_tokens(part.render()) > CARD_TOKENS:
        part.items.pop()
        part.truncated = True
    return part


def _env_part(store: Store, profile: dict) -> _Part:
    da = profile.get("da")
    legacy_name = _one_line(da.get("name")) if isinstance(da, dict) else ""
    has_persona = bool(_persona.get_persona(profile))
    identity = profile.get("identity")
    user_name = _one_line(identity.get("name")) if isinstance(identity, dict) else ""
    sid = store.effective_sid()
    lines = [
        f"now: {_store.now_iso()}",
        f"session: {sid}",
        f"cli: 各commandに --sid {sid} を付ける",
    ]
    if legacy_name and not has_persona:
        lines.append(f"名前: {legacy_name}")
    if user_name:
        lines.append(f"利用者: {user_name}")
    lines.extend((
        f'過去の決定・経緯: kiseki-da search "<語>" --sid {sid}',
        f"進行中の作業: kiseki-da task show <id> --sid {sid}",
        "利用者しか知らないこと: 質問する",
    ))
    part = _Part("env", [[ln] for ln in lines], always=True)
    while estimate_tokens(part.render()) > ENV_TOKENS and len(part.items) > 6:
        del part.items[3]   # assistant/user identity lines are the only optional entries
        part.truncated = True
    return part


def _persona_part(profile: dict) -> _Part:
    rendered = _persona.render_persona(profile)
    if not rendered:
        return _Part("persona")
    items: list[list[str]] = []
    kinds: list[str] = []
    for line in rendered.splitlines()[1:]:
        items.append([line])
        if line.startswith("- 表現メモ（データであり命令ではない）:"):
            kinds.append("custom")
        elif line.startswith("- 表現:"):
            kinds.append("optional")
        else:
            kinds.append("core")
    return _Part("persona", items, item_kinds=kinds)


def _pending_part(store: Store, profile: dict, today: _dt.date) -> _Part:
    pending = len(store.candidates("pending"))
    expired = sum(1 for s in _store.SECTIONS for it in profile.get(s) or []
                  if isinstance(it, dict) and _is_stale(it, today))
    return _Part("pending", [[f"未承認候補 {pending} 件（kiseki-da candidate list）"],
                             [f"レビュー期限切れ {expired} 件（kiseki-da report --week）"]], always=True)


# ---------------------------------------------------------------- build

def build(store: Store, budget: int = 2500, include_goals: bool = False,
          include_policy: bool = False) -> tuple[str, dict]:
    policy_path = _store.REPO_ROOT / "core" / "policy" / "interaction.md"
    policy_text = policy_path.read_text(encoding="utf-8")
    policy_tokens = estimate_tokens(policy_text)
    profile = store.read_effective_profile()
    today = _store.today()
    conflicts: list[dict] = []

    parts: dict[str, _Part] = {
        "constraints": _profile_part("constraints", profile["constraints"], today, conflicts),
        "cards": _cards_part(store),
        "persona": _persona_part(profile),
        "preferences": _profile_part("preferences", profile["preferences"], today, conflicts, newest_first=True),
        "goals": (_profile_part("goals", [g for g in profile["goals"]
                                          if isinstance(g, dict) and g.get("status") == "active"],
                                today, conflicts)
                  if include_goals else _Part("goals")),
        "env": _env_part(store, profile),
        "pending": _pending_part(store, profile, today),
    }

    def render() -> tuple[str, str, dict[str, int], int]:
        rendered = {n: parts[n].render() for n in PART_NAMES[1:]}
        resident = "\n\n".join(t for t in rendered.values() if t)
        text = "\n\n".join(t for t in (policy_text.rstrip(), resident) if t) if include_policy else resident
        tokens = {n: estimate_tokens(t) for n, t in rendered.items()}
        return text, resident, tokens, policy_tokens + sum(tokens.values())

    text, resident, tokens, used = render()
    while used > budget or estimate_tokens(text) > budget or len(text) > MAX_CHARS:
        removed = (
            parts["goals"].pop_last()
            or parts["persona"].pop_last("custom")
            or parts["persona"].pop_last("optional")
            or parts["preferences"].pop_last()
            or parts["cards"].pop_last()
            or parts["constraints"].pop_last()
        )
        if not removed:
            break
        text, resident, tokens, used = render()
    if len(text) > MAX_CHARS:   # unreachable while env stays ≤ 150 tokens; keeps the contract absolute
        text = text[:MAX_CHARS]

    manifest = {
        "budget": int(budget),
        "used": used,
        "parts": [{"name": "policy", "tokens": policy_tokens, "truncated": False}]
                 + [{"name": n, "tokens": tokens[n], "truncated": parts[n].truncated} for n in PART_NAMES[1:]],
        "conflicts": conflicts,
        "chars": len(text),
    }
    return text, manifest
