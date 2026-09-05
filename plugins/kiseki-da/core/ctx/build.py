"""build.py — bounded resident context and plugin SessionStart policy.

Direct ``build`` calls count but do not render policy for compatibility.  Plugin
SessionStart passes ``include_policy=True`` so the same policy is injected once.
"""
from __future__ import annotations

import datetime as _dt
import shlex
import sys
from dataclasses import dataclass, field

from core.ctx import store as _store
from core.ctx import persona as _persona
from core.ctx import taskcard
from core.ctx import evidence as E
from core.ctx.store import Store, estimate_tokens

PART_NAMES = ("policy", "constraints", "cards", "persona", "preferences", "goals", "env", "pending")

MAX_CHARS = 9000
LINE_LIMITS = {"preferences": 10, "goals": 5}
CARD_LIMIT = 2
CARD_TOKENS = 400
ENV_TOKENS = 240
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
    total: int = 0

    def __post_init__(self):
        self.total = max(self.total, len(self.items))

    def render(self) -> str:
        if not self.items and not self.always and not self.truncated:
            return ""
        lines = [HEADINGS[self.name]]
        for item in self.items:
            lines.extend(item)
        if self.truncated:
            omitted = max(0, self.total - len(self.items))
            if self.name == "constraints":
                lines.append(f"必須制約 {omitted} 項目を省略。kiseki-da context required で全ページを読み、取得後に変更作業へ進む。")
            elif self.name == "cards":
                lines.append("作業の詳細を省略。各カードの kiseki-da task show と kiseki-da task list --json で確認する。")
            else:
                lines.append(f"{omitted} 項目を省略。kiseki-da search または kiseki-da context profile で詳細を確認する。")
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

def command_prefix(home):
    """A quoted, fixed runtime entry point independent of cwd and PATH."""
    return shlex.join([sys.executable, str(_store.REPO_ROOT / "core/ctx/cli.py"), "--home", str(home)])


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
        local = [m for m in members if m.get("scope") == "workspace"]
        if local:
            members = local  # a scoped exception leaves the global rule intact for other projects
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
    limit = LINE_LIMITS.get(name, len(part.items))
    if len(part.items) > limit:
        del part.items[limit:]
        part.truncated = True
    return part


# ---------------------------------------------------------------- cards / env / pending

def _card_lines(card: taskcard.TaskCard) -> list[str]:
    def short(value, n=100):
        text = _one_line(value)
        return text if len(text) <= n else text[:n] + "…"
    lines = [f"- {card.id} [{card.risk}] {short(card.goal)}"]
    if card.next_action:
        lines.append(f"  次: {short(card.next_action)}")
    pending = [c for c in card.criteria if c.status != "pass"]
    if pending:
        lines.append(f"  未達 {len(pending)} 件: {pending[0].id} {short(pending[0].claim, 70)}")
    if card.questions:
        lines.append(f"  未確定 {len(card.questions)} 件: {short(card.questions[0], 70)}")
    if card.decisions:
        lines.append(f"  決定: {short(card.decisions[-1], 70)}")
    lines.append(f"  詳細: kiseki-da task show {card.id}")
    return lines


def current_cards(store: Store) -> list[taskcard.TaskCard]:
    open_cards: list[taskcard.TaskCard] = []
    workspace = store.workspace()
    if not workspace:
        return []
    for tid in store.list_tasks():
        try:
            card = taskcard.load(store, tid)
        except (OSError, ValueError, _store.UserError):
            continue   # one unreadable card (not UTF-8, no permission) must not empty the whole block; same guard as search
        if card.status == "open" and card.workspace == workspace:
            open_cards.append(card)
    open_cards.sort(key=lambda c: (c.updated, c.id), reverse=True)   # newest `updated` first, as taskcard.list_cards
    return open_cards


def _shrink_card(part: _Part) -> bool:
    for item in reversed(part.items):
        if len(item) > 2:
            item.pop(-2)
            part.truncated = True
            return True
    return False


def _cards_part(store: Store) -> _Part:
    open_cards = current_cards(store)
    part = _Part("cards", [_card_lines(c) for c in open_cards[:CARD_LIMIT]])
    part.total = len(open_cards)
    part.truncated = bool(open_cards)
    while estimate_tokens(part.render()) > CARD_TOKENS and _shrink_card(part):
        pass
    return part


def scoped_profile(store: Store) -> dict:
    profile = store.read_effective_profile()
    workspace = store.workspace()
    for name in _store.SECTIONS:
        profile[name] = [it for it in profile[name] if isinstance(it, dict)
                         and (it.get("scope", "global") == "global"
                              or bool(workspace) and it.get("workspace") == workspace)]
    return profile


def required_context(store: Store) -> dict:
    profile = scoped_profile(store)
    part = _profile_part("constraints", profile["constraints"], _store.today(), [])
    lines = [line for item in part.items for line in item]
    for card in current_cards(store)[:CARD_LIMIT]:
        lines.extend(f"- {card.id}: {c}" for c in card.constraints)
    text = "\n".join(lines)
    pages = [text[i:i + 3500] for i in range(0, len(text), 3500)] or [""]
    return {"hash": E.digest({"workspace": store.workspace(), "text": text}),
            "text": text, "pages": pages, "workspace": store.workspace()}


def needs_context(store: Store) -> bool:
    required = required_context(store)
    if not required["text"]:
        return False
    read = set()
    for ev in store.iter_events(sid=store.effective_sid()):
        if ev.get("type") == "context_manifest":
            ref = ev.get("required_context", {})
            if ref.get("hash") == required["hash"] and ref.get("complete"):
                return False
        if ev.get("type") == "context_read" and ev.get("content_hash") == required["hash"]:
            read.add(ev.get("page"))
    return not set(range(1, len(required["pages"]) + 1)).issubset(read)


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
        f"kiseki-da = {command_prefix(store.common_home)}",
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
    while estimate_tokens(part.render()) > ENV_TOKENS:
        optional = next((i for i, item in enumerate(part.items)
                         if item[0].startswith(("名前:", "利用者:"))), None)
        if optional is None:
            break
        del part.items[optional]
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
    policy_text = (_store.REPO_ROOT / "core/policy/interaction.md").read_text(encoding="utf-8")
    policy_tokens = estimate_tokens(policy_text)
    profile = scoped_profile(store)
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
    for card in current_cards(store)[:CARD_LIMIT]:
        parts["constraints"].items.extend([[f"- {card.id}: {c}"] for c in card.constraints])
    parts["constraints"].total = len(parts["constraints"].items)

    def render() -> tuple[str, str, dict[str, int], int]:
        rendered = {n: parts[n].render() for n in PART_NAMES[1:]}
        resident = "保存済みの利用者条件と作業記録です。現在の明示指示を優先します。\n\n" + "\n\n".join(t for t in rendered.values() if t)
        text = policy_text.rstrip() + "\n\n" + resident if include_policy else resident
        tokens = {n: estimate_tokens(t) for n, t in rendered.items()}
        used = estimate_tokens(policy_text.rstrip() + "\n\n" + resident)
        tokens["env"] += used - policy_tokens - sum(tokens.values())
        return text, resident, tokens, used

    text, resident, tokens, used = render()
    while used > budget or len(text) > MAX_CHARS:
        removed = (parts["goals"].pop_last()
                   or parts["persona"].pop_last("custom")
                   or parts["persona"].pop_last("optional")
                   or parts["preferences"].pop_last()
                   or _shrink_card(parts["cards"])
                   or parts["constraints"].pop_last())
        if not removed:
            raise _store.UserError("必須の参照情報が予算に収まりません。--budget を増やしてください。情報を黙って削除しません")
        text, resident, tokens, used = render()
    required = required_context(store)

    manifest = {
        "budget": int(budget),
        "used": used,
        "parts": [{"name": "policy", "tokens": policy_tokens, "truncated": False}]
                 + [{"name": n, "tokens": tokens[n], "truncated": parts[n].truncated} for n in PART_NAMES[1:]],
        "conflicts": conflicts,
        "chars": len(text),
        "required_context": {"hash": required["hash"], "complete": not parts["constraints"].truncated,
                             "pages": len(required["pages"])},
        "resident_profile_ids": [it["id"] for section in _store.SECTIONS for it in profile[section]
                                 if isinstance(it.get("id"), str)
                                 and f"{_one_line(it.get('text'))}（{it['id']}）" in text],
    }
    return text, manifest
