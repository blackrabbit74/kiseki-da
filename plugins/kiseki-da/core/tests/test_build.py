"""test_build.py — resident block: used ≤ 2,500, policy part, stale exclusion, key conflicts, budget cuts,
`未承認候補` / `session:` lines, chars ≤ 9,000, open cards (INTERFACES §10)."""
from __future__ import annotations

import contextlib
import datetime as dt
import io
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from core.ctx import build as B
from core.ctx import store as S
from core.ctx import taskcard
from core.ctx.store import Store

FX = Path(__file__).resolve().parent / "fixtures"
POLICY_REL = Path("core") / "policy" / "interaction.md"
C1_LINE = "- 本番 DB への直接書込は禁止。マイグレーション経由のみ（c1）"
CONFLICT_LINE = "- ⚠ 衝突: コミットメッセージは英語で書く（p1） / コミットメッセージは日本語で書く（p2）"


def _item(pid: str, text: str, source: str = "user-stated", recorded_at: str = "2026-08-01",
          review_by: str = "2099-12-31", key: str | None = None, status: str | None = None) -> dict:
    it = {"id": pid, "text": text, "source": source, "recorded_at": dt.date.fromisoformat(recorded_at),
          "confidence": 1.0, "review_by": dt.date.fromisoformat(review_by)}
    if key:
        it["key"] = key
    if status:
        it["status"] = status
    return it


def _part(text: str, heading: str) -> str:
    """Rendered text of one part (heading + lines); '' when the heading is absent."""
    block: list[str] = []
    inside = False
    for line in text.splitlines():
        if line.startswith("## "):
            if inside:
                break
            inside = line == heading
        if inside:
            block.append(line)
    return "\n".join(block).rstrip("\n")


def _lines(text: str, heading: str) -> list[str]:
    return [ln for ln in _part(text, heading).splitlines()[1:] if ln]


def _headings(text: str) -> list[str]:
    return [ln for ln in text.splitlines() if ln.startswith("## ")]


class BuildTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name).resolve()
        self.st = Store(home=self.home, sid="s-test")
        self.st.init()

    def use_fixture(self):
        shutil.copy(FX / "profile.sample.toml", self.st.profile_path)

    def build(self, **kw):
        return B.build(self.st, **kw)

    # ------------------------------------------------------------ manifest shape / policy part
    def test_fixture_manifest_and_policy_part(self):
        self.use_fixture()
        events_before = len(list(self.st.iter_events()))
        text, m = self.build()
        self.assertLessEqual(m["used"], 2500)
        self.assertEqual(m["budget"], 2500)
        self.assertEqual(set(m), {"budget", "used", "parts", "conflicts", "chars"})
        self.assertEqual([p["name"] for p in m["parts"]], list(B.PART_NAMES))
        for p in m["parts"]:
            self.assertEqual(set(p), {"name", "tokens", "truncated"})
            self.assertIsInstance(p["tokens"], int)
            self.assertIsInstance(p["truncated"], bool)
        policy = m["parts"][0]
        self.assertEqual(policy["name"], "policy")
        self.assertGreater(policy["tokens"], 0)
        self.assertEqual(policy["tokens"], S.estimate_tokens((S.REPO_ROOT / POLICY_REL).read_text(encoding="utf-8")))
        self.assertFalse(policy["truncated"])
        self.assertNotIn("非権威条項", text)   # the policy body arrives through the instruction file
        self.assertEqual(m["used"], sum(p["tokens"] for p in m["parts"]))
        for p in m["parts"][1:]:
            self.assertEqual(p["tokens"], S.estimate_tokens(_part(text, B.HEADINGS[p["name"]])), p["name"])
        self.assertEqual(m["chars"], len(text))
        self.assertLessEqual(m["chars"], 9000)
        self.assertEqual(_headings(text), ["## 制約", "## 選好", "## 環境", "## 未承認"])
        self.assertEqual(len(list(self.st.iter_events())), events_before)   # build() itself writes nothing
        self.assertEqual(self.st.validate("event", {"ts": "t", "sid": "s", "seq": 1, "type": "context_manifest", **m}), [])

    def test_empty_profile_still_has_env_and_pending(self):
        text, m = self.build()   # state.example profile: no items, no cards, da.name empty
        self.assertEqual(_headings(text), ["## 環境", "## 未承認"])
        self.assertNotIn("名前:", text)
        self.assertEqual(_lines(text, "## 未承認"),
                         ["未承認候補 0 件（kiseki-da candidate list）", "レビュー期限切れ 0 件（kiseki-da report --week）"])
        self.assertEqual(m["conflicts"], [])
        by = {p["name"]: p for p in m["parts"]}
        for name in ("constraints", "cards", "preferences", "goals"):
            self.assertEqual(by[name], {"name": name, "tokens": 0, "truncated": False})
        self.assertLessEqual(m["used"], 2500)

    # ------------------------------------------------------------ stale items
    def test_stale_items_are_excluded(self):
        self.use_fixture()
        text, m = self.build()
        self.assertEqual(_lines(text, "## 制約"), [C1_LINE])
        self.assertNotIn("（c2）", text)
        self.assertNotIn("旧 API v1", text)
        self.assertFalse(m["parts"][1]["truncated"])   # exclusion is not truncation

    def test_review_by_forms(self):
        today = S.today()
        yesterday = today - dt.timedelta(days=1)

        def block(pid: str, text: str, review_by: str | None) -> list[str]:
            lines = ["[[constraints]]", f'id = "{pid}"', f'text = "{text}"', 'source = "user-stated"',
                     "recorded_at = 2026-08-01", "confidence = 1.0"]
            if review_by is not None:
                lines.append(f"review_by = {review_by}")
            return lines
        toml = ["schema = 1", "[identity]", 'name = ""', "[da]", 'name = ""']
        toml += block("c1", "期限なし", None)
        toml += block("c2", "文字列の昨日", f'"{yesterday.isoformat()}"')
        toml += block("c3", "壊れた日付", '"いつか"')
        toml += block("c4", "今日が期限", today.isoformat())
        toml += block("c5", "昨日が期限", yesterday.isoformat())
        toml += block("c6", "日時つき", f"{yesterday.isoformat()}T09:00:00+09:00")
        self.st.write_text("profile.toml", "\n".join(toml) + "\n")
        text, m = self.build()
        self.assertEqual(_lines(text, "## 制約"), ["- 期限なし（c1）", "- 壊れた日付（c3）", "- 今日が期限（c4）"])
        self.assertIn("レビュー期限切れ 3 件（kiseki-da report --week）", text)
        self.assertFalse(m["parts"][1]["truncated"])

    # ------------------------------------------------------------ key conflicts
    def test_key_conflicts_in_fixture(self):
        self.use_fixture()
        text, m = self.build()
        prefs = _lines(text, "## 選好")
        self.assertEqual(prefs, [
            "- インデントはスペース 4 つ（p4）",   # 2026-08-26
            "- 説明は結論を先に書く（p3）",         # 2026-08-25
            CONFLICT_LINE,                          # newest member 2026-08-20; ids in profile order
        ])
        self.assertEqual(m["conflicts"], [{"key": "commit-lang", "ids": ["p1", "p2"]}])
        self.assertNotIn("（p5）", text)            # approved-inference loses to user-stated silently
        self.assertNotIn("インデントはタブ", text)
        self.assertFalse(m["parts"][4]["truncated"])

    def test_conflict_resolution_variants(self):
        yesterday = (S.today() - dt.timedelta(days=1)).isoformat()
        prof = self.st.read_profile()
        prof["constraints"] = [
            _item("c1", "制約 A", key="k1"),
            _item("c2", "無関係"),
            _item("c3", "制約 B", key="k1"),                                  # same rank as c1 → conflict
            _item("c4", "制約 C", key="k1", source="document:x"),             # lower rank → dropped silently
            _item("c5", "推論 D", key="k2", source="approved-inference"),
            _item("c6", "文書 E", key="k2", source="document:y"),             # loses to c5, no conflict
            _item("c7", "失効 F", key="k3", review_by=yesterday),             # stale partner → no conflict
            _item("c8", "現役 G", key="k3"),
            _item("c9", "三つ目\nの行", key="k1"),                            # third winner, text collapsed
        ]
        prof["goals"] = [_item("g1", "目標 A", key="kg", status="active"),
                         _item("g2", "目標 B", key="kg", status="active"),
                         _item("g3", "目標 C", key="kg", status="done")]      # not active → not considered
        self.st.write_profile(prof)
        text, m = self.build()
        self.assertEqual(_lines(text, "## 制約"), [
            "- ⚠ 衝突: 制約 A（c1） / 制約 B（c3） / 三つ目 の行（c9）",
            "- 無関係（c2）",
            "- 推論 D（c5）",
            "- 現役 G（c8）",
        ])
        self.assertEqual(m["conflicts"], [{"key": "k1", "ids": ["c1", "c3", "c9"]}])   # goals not built
        self.assertFalse(m["parts"][1]["truncated"])
        text, m = self.build(include_goals=True)
        self.assertEqual(_lines(text, "## 目標"), ["- ⚠ 衝突: 目標 A（g1） / 目標 B（g2）"])
        self.assertEqual(m["conflicts"], [{"key": "k1", "ids": ["c1", "c3", "c9"]},
                                          {"key": "kg", "ids": ["g1", "g2"]}])

    # ------------------------------------------------------------ fixture horizon
    def test_fixture_review_by_horizon(self):
        # INTERFACES §1: the sample profile carries exactly one expired item. Staleness is judged
        # against the wall clock (store.today), so every other review_by — and the _item() default —
        # must stay at least five years out, or the stale-exclusion assertions fail on a fixed date.
        self.use_fixture()
        today = S.today()
        horizon = today + dt.timedelta(days=5 * 366)
        prof = self.st.read_profile()
        expired, near = [], []
        for section in ("constraints", "preferences", "goals", "facts"):
            for it in prof[section]:
                if it["review_by"] < today:
                    expired.append(it["id"])
                elif it["review_by"] < horizon:
                    near.append(it["id"])
        self.assertEqual(expired, ["c2"])
        self.assertEqual(near, [])
        self.assertGreaterEqual(_item("x1", "既定")["review_by"], horizon)

    # ------------------------------------------------------------ goals
    def test_goals_only_when_requested(self):
        self.use_fixture()
        text, m = self.build()
        self.assertNotIn("## 目標", text)
        self.assertNotIn("（g1）", text)
        self.assertEqual(m["parts"][5], {"name": "goals", "tokens": 0, "truncated": False})
        text, m = self.build(include_goals=True)
        self.assertEqual(_lines(text, "## 目標"), ["- 10 月末までに社内 CLI を v1 として配布する（g1）"])
        self.assertNotIn("（g2）", text)   # status = "done"
        self.assertGreater(m["parts"][5]["tokens"], 0)
        self.assertFalse(m["parts"][5]["truncated"])
        self.assertEqual(_headings(text), ["## 制約", "## 選好", "## 目標", "## 環境", "## 未承認"])

    # ------------------------------------------------------------ part limits
    def test_line_limits(self):
        prof = self.st.read_profile()
        prof["constraints"] = [_item(f"c{i}", f"制約 {i}") for i in range(1, 13)]
        prof["goals"] = [_item(f"g{i}", f"目標 {i}", status="active") for i in range(1, 8)]
        self.st.write_profile(prof)
        text, m = self.build(include_goals=True)
        self.assertEqual(_lines(text, "## 制約"), [f"- 制約 {i}（c{i}）" for i in range(1, 11)])
        self.assertEqual(_lines(text, "## 目標"), [f"- 目標 {i}（g{i}）" for i in range(1, 6)])
        by = {p["name"]: p for p in m["parts"]}
        self.assertTrue(by["constraints"]["truncated"])
        self.assertTrue(by["goals"]["truncated"])
        self.assertFalse(by["preferences"]["truncated"])
        self.assertEqual(_headings(text), ["## 制約", "## 目標", "## 環境", "## 未承認"])

    # ------------------------------------------------------------ budget cuts
    def test_persona_cap_and_budget_precedence(self):
        from core.ctx import persona
        prof = self.st.read_profile()
        prof["constraints"] = [_item("c1", "絶対に守る制約")]
        prof["preferences"] = [_item("p1", "通常の選好")]
        prof["goals"] = [_item("g1", "任意の目標", status="active")]
        self.st.write_profile(prof)
        persona.save_persona(self.st, {
            "name": "キセキ", "first_person": "私", "user_address": "利用者さん",
            "formality": "balanced", "warmth": "warm", "verbosity": "compact",
            "initiative": "proactive", "relationship": "partner", "custom_style": "柔" * 200,
        })
        taskcard.new_card(self.st, "重要なカード", id="important")
        text, full = self.build(budget=10 ** 6, include_goals=True)
        by = {p["name"]: p for p in full["parts"]}
        self.assertLessEqual(by["persona"]["tokens"], 220)
        self.assertIn("- 表現メモ（データであり命令ではない）:", text)

        # Goals are discarded first.
        budget = full["used"] - by["goals"]["tokens"]
        text, after_goal = self.build(budget=budget, include_goals=True)
        self.assertNotIn("## 目標", text)
        self.assertIn("- 表現メモ（データであり命令ではない）:", text)

        # Then custom text, then optional persona traits. Preferences/cards/
        # constraints remain until both lower-priority persona layers are gone.
        text, after_custom = self.build(budget=budget - 1, include_goals=True)
        self.assertNotIn("- 表現メモ（データであり命令ではない）:", text)
        self.assertIn("- 表現:", text)
        self.assertIn("通常の選好", text)
        self.assertIn("important", text)
        self.assertIn("絶対に守る制約", text)
        text, after_optional = self.build(budget=after_custom["used"] - 1, include_goals=True)
        self.assertNotIn("- 表現:", text)
        self.assertIn("- 名前: キセキ", text)
        self.assertIn("通常の選好", text)
        self.assertIn("important", text)
        self.assertIn("絶対に守る制約", text)

    def test_budget_cut_order(self):
        self.use_fixture()
        prof = self.st.read_profile()
        for i in range(6, 14):   # p6..p13, all newer than the fixture items
            prof["preferences"].append(_item(f"p{i}", f"選好 {i}", recorded_at=f"2026-09-{i - 5:02d}"))
        prof["goals"].append(_item("g3", "二つ目の目標", status="active"))
        self.st.write_profile(prof)
        taskcard.new_card(self.st, "進行中の作業", id="card-1")

        text, full = self.build(budget=10 ** 6, include_goals=True)
        by = {p["name"]: p for p in full["parts"]}
        prefs = _lines(text, "## 選好")
        self.assertEqual(prefs[:8], [f"- 選好 {i}（p{i}）" for i in range(13, 5, -1)])   # recorded_at desc
        self.assertEqual(prefs[8:], ["- インデントはスペース 4 つ（p4）", "- 説明は結論を先に書く（p3）"])
        self.assertTrue(by["preferences"]["truncated"])   # 11 entries, 10 lines: the oldest (⚠) fell off
        self.assertNotIn("⚠ 衝突", text)
        self.assertEqual(full["conflicts"], [{"key": "commit-lang", "ids": ["p1", "p2"]}])   # still reported
        self.assertEqual(len(_lines(text, "## 目標")), 2)
        self.assertFalse(by["goals"]["truncated"])
        self.assertIn("- card-1 [R1] 進行中の作業", text)

        # 1) short by exactly the goals' tokens: goals go, nothing else moves
        budget = full["used"] - by["goals"]["tokens"]
        text, m = self.build(budget=budget, include_goals=True)
        by2 = {p["name"]: p for p in m["parts"]}
        self.assertEqual(m["used"], budget)
        self.assertEqual(by2["goals"], {"name": "goals", "tokens": 0, "truncated": True})
        self.assertNotIn("## 目標", text)
        self.assertEqual(_lines(text, "## 選好"), prefs)
        self.assertEqual(by2["preferences"]["tokens"], by["preferences"]["tokens"])
        self.assertIn("card-1", text)
        self.assertIn("（c1）", text)

        # 2) one token less: the last preference line goes next (goals → preferences)
        text, m = self.build(budget=budget - 1, include_goals=True)
        by2 = {p["name"]: p for p in m["parts"]}
        self.assertLessEqual(m["used"], budget - 1)
        self.assertEqual(_lines(text, "## 選好"), prefs[:-1])
        self.assertTrue(by2["preferences"]["truncated"])
        self.assertIn("card-1", text)
        self.assertIn("（c1）", text)
        self.assertFalse(by2["cards"]["truncated"])
        self.assertFalse(by2["constraints"]["truncated"])

        # 3) cards go before constraints
        budget = full["used"] - by["goals"]["tokens"] - by["preferences"]["tokens"] - by["cards"]["tokens"]
        text, m = self.build(budget=budget, include_goals=True)
        by2 = {p["name"]: p for p in m["parts"]}
        self.assertEqual(m["used"], budget)
        self.assertEqual(_headings(text), ["## 制約", "## 環境", "## 未承認"])
        self.assertEqual(_lines(text, "## 制約"), [C1_LINE])
        self.assertTrue(by2["cards"]["truncated"])
        self.assertFalse(by2["constraints"]["truncated"])

        # 4) a budget just above the policy: everything cuttable is gone, env and pending are untouched
        policy_tokens = by["policy"]["tokens"]
        text, m = self.build(budget=policy_tokens + 1, include_goals=True)
        by2 = {p["name"]: p for p in m["parts"]}
        for name in ("constraints", "cards", "preferences", "goals"):
            self.assertEqual(by2[name]["tokens"], 0, name)
            self.assertTrue(by2[name]["truncated"], name)
        for name in ("env", "pending"):
            self.assertGreater(by2[name]["tokens"], 0, name)
            self.assertFalse(by2[name]["truncated"], name)
        self.assertEqual(_headings(text), ["## 環境", "## 未承認"])
        self.assertIn("session: s-test", text)
        self.assertIn("未承認候補 0 件（kiseki-da candidate list）", text)
        self.assertEqual(m["used"], policy_tokens + by2["env"]["tokens"] + by2["pending"]["tokens"])
        self.assertGreater(m["used"], m["budget"])   # policy / env / pending are never cut
        self.assertEqual(m["chars"], len(text))

    # ------------------------------------------------------------ pending part
    def test_pending_lines(self):
        self.use_fixture()
        text, _ = self.build()
        self.assertEqual(_lines(text, "## 未承認"),
                         ["未承認候補 0 件（kiseki-da candidate list）", "レビュー期限切れ 1 件（kiseki-da report --week）"])
        cid = self.st.append_candidate({"text": "日時は ISO 8601", "source": "user-stated"})
        text, _ = self.build()
        self.assertIn("未承認候補 1 件（kiseki-da candidate list）", text)
        self.st.reject(cid)
        text, _ = self.build()
        self.assertIn("未承認候補 0 件（kiseki-da candidate list）", text)
        # the expired count spans all four sections, whatever the item's status
        prof = self.st.read_profile()
        prof["facts"].append(_item("f2", "古い事実", review_by="2020-01-01"))
        prof["goals"].append(_item("g3", "古い目標", status="done", review_by="2020-01-01"))
        self.st.write_profile(prof)
        text, _ = self.build()
        self.assertIn("レビュー期限切れ 3 件（kiseki-da report --week）", text)
        self.assertNotIn("古い事実", text)

    # ------------------------------------------------------------ env part
    def test_env_lines_and_session(self):
        self.use_fixture()
        text, m = self.build()
        env = _lines(text, "## 環境")
        self.assertTrue(env[0].startswith("now: "))
        self.assertIsNotNone(S.parse_ts(env[0][len("now: "):]))
        self.assertEqual(env[1], "session: s-test")
        self.assertEqual(env[2], "cli: 各commandに --sid s-test を付ける")
        self.assertEqual(env[3], "名前: ナビ")
        self.assertEqual(env[4], "利用者: テスト太郎")
        self.assertEqual(env[5:], ['過去の決定・経緯: kiseki-da search "<語>" --sid s-test',
                                   "進行中の作業: kiseki-da task show <id> --sid s-test",
                                   "利用者しか知らないこと: 質問する"])
        self.assertLessEqual(m["parts"][6]["tokens"], 150)
        self.assertFalse(m["parts"][6]["truncated"])
        # `session:` follows effective_sid(): --sid > session/current > "nosession"
        anon = Store(home=self.home)
        self.assertIn("session: nosession", B.build(anon)[0])
        anon.set_current_sid("s-current")
        self.assertIn(f"session: {anon.effective_sid()}", B.build(anon)[0])
        self.assertIn("session: s-current", B.build(anon)[0])
        self.assertIn(f"session: {self.st.effective_sid()}", B.build(self.st)[0])
        self.assertIn("session: s-test", B.build(self.st)[0])   # explicit sid wins over session/current

    def test_env_drops_name_line_over_150_tokens(self):
        prof = self.st.read_profile()
        prof["da"]["name"] = "名" * 400
        self.st.write_profile(prof)
        text, m = self.build()
        self.assertNotIn("名前:", text)
        self.assertLessEqual(m["parts"][6]["tokens"], 150)
        self.assertTrue(m["parts"][6]["truncated"])
        self.assertIn("session: s-test", text)

    # ------------------------------------------------------------ policy path
    def test_missing_policy_raises(self):
        self.use_fixture()
        with tempfile.TemporaryDirectory() as other:
            root = Path(other).resolve()
            with mock.patch.object(S, "REPO_ROOT", root):
                with self.assertRaises(FileNotFoundError):
                    self.build()
                # REPO_ROOT is read at call time: a policy under the patched root is what gets counted
                (root / POLICY_REL).parent.mkdir(parents=True)
                (root / POLICY_REL).write_text("# 方針\n- 短い。\n", encoding="utf-8")
                text, m = self.build()
                self.assertEqual(m["parts"][0]["tokens"], S.estimate_tokens("# 方針\n- 短い。\n"))
                self.assertIn("cli: 各commandに --sid s-test を付ける", text)

    # ------------------------------------------------------------ cards
    def test_open_cards(self):
        self.use_fixture()
        a = taskcard.new_card(self.st, "古い作業\n2 行目は載せない", risk="R0", id="a-old")
        b = taskcard.new_card(self.st, "中間の作業", id="b-mid")
        c = taskcard.new_card(self.st, "新しい作業", risk="R2", kind="research", id="c-new")
        for card, claim in ((a, "A の条件"), (b, "B の条件"), (c, "C の条件")):
            card.criteria.append(taskcard.Criterion(id="C1", claim=claim, check="pytest -q", evidence="-", status="open"))
            taskcard.save(self.st, card, ["criterion:C1"])
        c.criteria.append(taskcard.Criterion(id="C2", claim="済んだ条件", check="Read git diff",
                                             evidence="ev:s-test:1", status="pass"))
        c.criteria.append(taskcard.Criterion(id="C3", claim="未検証の条件", check="pytest -q", evidence="-",
                                             status="unverified"))
        c.questions.append("再試行回数は？")
        c.assumptions.append("仮定は載せない")
        taskcard.save(self.st, c, ["criterion:C2", "criterion:C3", "question", "assumption"])
        text, m = self.build()
        self.assertEqual(_lines(text, "## 進行中"), [
            "- c-new [R2] 新しい作業",
            "  未達: C1 C の条件",
            "  未達: C3 未検証の条件",
            "  未確定: 再試行回数は？",
            "- b-mid [R1] 中間の作業",
            "  未達: C1 B の条件",
        ])
        self.assertNotIn("a-old", text)   # only the 2 most recently updated open cards
        self.assertNotIn("済んだ条件", text)
        self.assertNotIn("仮定は載せない", text)
        self.assertTrue(m["parts"][2]["truncated"])
        self.assertLessEqual(m["parts"][2]["tokens"], 400)
        self.assertEqual(_headings(text), ["## 制約", "## 進行中", "## 選好", "## 環境", "## 未承認"])
        # a closed card leaves the block; the goal shows its first line only
        c.status = "done"
        taskcard.save(self.st, c, ["status:done"])
        text, m = self.build()
        self.assertEqual(_lines(text, "## 進行中"), [
            "- b-mid [R1] 中間の作業",
            "  未達: C1 B の条件",
            "- a-old [R0] 古い作業",
            "  未達: C1 A の条件",
        ])
        self.assertNotIn("c-new", text)
        self.assertNotIn("2 行目は載せない", text)
        self.assertFalse(m["parts"][2]["truncated"])

    def test_cards_part_token_limit(self):
        self.use_fixture()
        taskcard.new_card(self.st, "a" * 1000, id="first")    # ≈ 250 tokens each
        taskcard.new_card(self.st, "b" * 1000, id="second")
        text, m = self.build()
        lines = _lines(text, "## 進行中")
        self.assertEqual(len(lines), 1)
        self.assertTrue(lines[0].startswith("- second [R1] bbbb"))   # newest first, the older one dropped
        self.assertNotIn("first", text)
        self.assertTrue(m["parts"][2]["truncated"])
        self.assertLessEqual(m["parts"][2]["tokens"], 400)

    def test_unreadable_cards_are_skipped(self):
        """A card file that is not valid UTF-8 or cannot be read is skipped, even when it is closed: the rest of
        the block (constraints, other cards, env, pending) still reaches the session and `ctx build` exits 0."""
        from core.ctx import cli
        self.use_fixture()
        taskcard.new_card(self.st, "生きている作業", id="alive")
        tasks = self.home / "tasks"
        cp932 = "テスト".encode("cp932")   # b"\x83\x65\x83\x58\x83\x67": an external editor re-saved the file
        (tasks / "done-cp932.md").write_bytes(b"id: done-cp932\nstatus: done\nrisk: R1\n\n# Goal\n" + cp932 + b"\n")
        (tasks / "open-cp932.md").write_bytes(b"id: open-cp932\nstatus: open\nrisk: R1\n\n# Goal\n" + cp932 + b"\n")
        with self.assertRaises(UnicodeDecodeError):
            taskcard.load(self.st, "done-cp932")   # the loader itself stays strict
        text, m = self.build()
        self.assertEqual(_lines(text, "## 進行中"), ["- alive [R1] 生きている作業"])
        self.assertNotIn("cp932", text)
        self.assertEqual(_lines(text, "## 制約"), [C1_LINE])
        self.assertIn("session: s-test", text)
        self.assertIn("未承認候補 0 件（kiseki-da candidate list）", text)
        self.assertFalse(m["parts"][2]["truncated"])   # exclusion is not truncation
        self.assertEqual(_headings(text), ["## 制約", "## 進行中", "## 選好", "## 環境", "## 未承認"])
        # a card the process may not read (PermissionError) is skipped the same way
        if os.name != "nt" and not (hasattr(os, "geteuid") and os.geteuid() == 0):
            locked = taskcard.new_card(self.st, "読めない作業", id="locked")
            locked_path = tasks / "locked.md"
            self.addCleanup(locked_path.chmod, 0o644)
            locked_path.chmod(0)
            text, m = self.build()
            self.assertEqual(_lines(text, "## 進行中"), ["- alive [R1] 生きている作業"])
            self.assertNotIn(locked.id, text)
            self.assertFalse(m["parts"][2]["truncated"])
        # the CLI path used by the session-start hook: exit 0 with the block, not 内部エラー / an empty context
        buf = io.StringIO()
        with mock.patch.dict(os.environ, {"KISEKI_DA_HOME": str(self.home)}), contextlib.redirect_stdout(buf):
            rc = cli.main(["build", "--sid", "s-cli"])
        self.assertEqual(rc, 0)
        self.assertIn("- alive [R1] 生きている作業", buf.getvalue())
        self.assertIn(C1_LINE, buf.getvalue())

    # ------------------------------------------------------------ character cap
    def test_chars_never_exceed_9000(self):
        self.use_fixture()
        # (a) a card whose goal alone is far beyond 400 tokens is dropped by the part limit
        taskcard.new_card(self.st, "x" * 20000, id="long-goal")
        text, m = self.build(budget=10 ** 6)
        self.assertLessEqual(len(text), 9000)
        self.assertEqual(m["chars"], len(text))
        self.assertNotIn("long-goal", text)
        self.assertTrue(m["parts"][2]["truncated"])
        # (b) ten long preferences under an unlimited budget: the character cap alone cuts them
        prof = self.st.read_profile()
        prof["preferences"] = [_item(f"p{i}", "y" * 2000, recorded_at=f"2026-08-{i:02d}") for i in range(1, 11)]
        self.st.write_profile(prof)
        text, m = self.build(budget=10 ** 6)
        self.assertLessEqual(len(text), 9000)
        self.assertEqual(m["chars"], len(text))
        self.assertLessEqual(m["used"], 10 ** 6)
        self.assertTrue(m["parts"][4]["truncated"])
        self.assertGreater(m["parts"][4]["tokens"], 0)   # some preferences still fit
        self.assertIn("（p10）", text)                    # newest kept, oldest cut
        self.assertNotIn("（p1）", text)
        self.assertIn("session: s-test", text)
        self.assertIn("レビュー期限切れ 1 件", text)

    # ------------------------------------------------------------ CLI (P0 completion criterion)
    def test_cli_build_json_records_manifest(self):
        from core.ctx import cli
        self.use_fixture()
        buf = io.StringIO()
        with mock.patch.dict(os.environ, {"KISEKI_DA_HOME": str(self.home)}), contextlib.redirect_stdout(buf):
            rc = cli.main(["build", "--json", "--sid", "s-cli"])
        self.assertEqual(rc, 0)
        out = json.loads(buf.getvalue())
        self.assertLessEqual(out["manifest"]["used"], 2500)
        self.assertIn("session: s-cli", out["text"])
        self.assertEqual(out["manifest"]["chars"], len(out["text"]))
        evs = list(self.st.iter_events(types={"context_manifest"}))
        self.assertEqual(len(evs), 1)
        self.assertEqual(evs[0]["sid"], "s-cli")
        self.assertEqual(evs[0]["used"], out["manifest"]["used"])
        self.assertEqual(evs[0]["parts"], out["manifest"]["parts"])
        self.assertEqual(self.st.validate("event", evs[0]), [])
        buf = io.StringIO()
        with mock.patch.dict(os.environ, {"KISEKI_DA_HOME": str(self.home)}), contextlib.redirect_stdout(buf):
            rc = cli.main(["build", "--goals", "--budget", "100000"])
        self.assertEqual(rc, 0)
        self.assertIn("## 目標", buf.getvalue())
        self.assertIn("session: nosession", buf.getvalue())
        self.assertEqual(len(list(self.st.iter_events(types={"context_manifest"}))), 2)


if __name__ == "__main__":
    unittest.main()
