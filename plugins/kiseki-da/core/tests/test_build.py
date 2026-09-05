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

    def test_legacy_card_needs_explicit_workspace_assignment(self):
        """A pre-scope card stays readable, but its project must not be inferred from the next session."""
        text = (FX / "task.sample.md").read_text(encoding="utf-8")
        card = taskcard.parse(text)
        self.st.write_text(f"tasks/{card.id}.md", text)
        current = self.home / "project"
        current.mkdir()
        self.st.set_workspace(str(current))
        before = self.st.task_path(card.id).read_bytes()
        block, _ = self.build()
        self.assertNotIn(card.id, block)
        self.assertEqual(self.st.task_path(card.id).read_bytes(), before)
        taskcard.set_workspace(self.st, card, str(current))
        block, _ = self.build()
        self.assertIn(card.id, block)

    def test_standalone_cli_cards_use_the_current_folder(self):
        project_a = self.home / "project-a"
        project_b = self.home / "project-b"
        project_a.mkdir()
        project_b.mkdir()
        with mock.patch("pathlib.Path.cwd", return_value=project_a):
            card = taskcard.new_card(self.st, "STANDALONE_A_ONLY", id="standalone-a")
            self.assertEqual(card.workspace, str(project_a))
            self.assertIn(card.id, self.build()[0])
        with mock.patch("pathlib.Path.cwd", return_value=project_b):
            self.assertNotIn(card.id, self.build()[0])

    # ------------------------------------------------------------ manifest shape / policy part
    def test_fixture_manifest_and_policy_part(self):
        self.use_fixture()
        text, m = self.build()
        self.assertLessEqual(m['used'],2500)
        self.assertEqual(m['chars'],len(text))
        self.assertEqual([p['name'] for p in m['parts']],list(B.PART_NAMES))
        self.assertEqual(m['used'],sum(p['tokens'] for p in m['parts']))
        self.assertEqual(m['used'], S.estimate_tokens((S.REPO_ROOT / POLICY_REL).read_text().rstrip() + '\n\n' + text))
        self.assertEqual(m['parts'][0]['tokens'],S.estimate_tokens((S.REPO_ROOT / POLICY_REL).read_text()))
        self.assertNotIn('非権威条項',text)
        self.assertTrue(m['required_context']['complete'])
        self.assertIn('c1',m['resident_profile_ids'])
        self.assertEqual(len(list(self.st.iter_events())),0)

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
        self.assertFalse(m["parts"][3]["truncated"])

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
        self.assertEqual({p["name"]: p for p in m["parts"]}["goals"], {"name": "goals", "tokens": 0, "truncated": False})
        text, m = self.build(include_goals=True)
        self.assertEqual(_lines(text, "## 目標"), ["- 10 月末までに社内 CLI を v1 として配布する（g1）"])
        self.assertNotIn("（g2）", text)   # status = "done"
        self.assertGreater({p["name"]: p for p in m["parts"]}["goals"]["tokens"], 0)
        self.assertFalse({p["name"]: p for p in m["parts"]}["goals"]["truncated"])
        self.assertEqual(_headings(text), ["## 制約", "## 選好", "## 目標", "## 環境", "## 未承認"])

    # ------------------------------------------------------------ part limits
    def test_line_limits(self):
        prof=self.st.read_profile()
        prof['constraints']=[_item(f'c{i}',f'制約 {i}') for i in range(1,13)]
        prof['goals']=[_item(f'g{i}',f'目標 {i}',status='active') for i in range(1,8)]
        self.st.write_profile(prof)
        text,m=self.build(include_goals=True)
        self.assertEqual([x for x in _lines(text,'## 制約') if x.startswith('- ')],[f'- 制約 {i}（c{i}）' for i in range(1,13)])
        self.assertFalse(m['parts'][1]['truncated'])
        self.assertEqual(len([x for x in _lines(text,'## 目標') if x.startswith('- ')]),5)
        self.assertIn('省略',_part(text,'## 目標'))

    # ------------------------------------------------------------ budget cuts
    def test_budget_cut_order(self):
        self.use_fixture()
        prof=self.st.read_profile()
        prof['preferences']=[_item(f'p{i}','低優先の選好。'*80) for i in range(10)]
        self.st.write_profile(prof)
        card=taskcard.new_card(self.st,'現在の重要な作業',id='important')
        text,m=self.build(budget=1800)
        self.assertLessEqual(m['used'],1800)
        self.assertIn('important',text)
        self.assertIn('kiseki-da task show important',text)
        self.assertIn(C1_LINE,text)
        self.assertIn('省略',_part(text,'## 選好'))
        with self.assertRaises(S.UserError):
            self.build(budget=1)

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
        self.assertIn("cli: 各commandに --sid s-test を付ける", env)
        self.assertIn(f"kiseki-da = {B.command_prefix(self.home)}", env)
        self.assertIn("名前: ナビ", env)
        self.assertIn('過去の決定・経緯: kiseki-da search "<語>" --sid s-test', env)
        self.assertIn("利用者しか知らないこと: 質問する", env)
        self.assertLessEqual({p["name"]: p for p in m["parts"]}["env"]["tokens"], B.ENV_TOKENS)
        self.assertFalse({p["name"]: p for p in m["parts"]}["env"]["truncated"])
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
        self.assertLessEqual({p["name"]: p for p in m["parts"]}["env"]["tokens"], B.ENV_TOKENS)
        self.assertTrue({p["name"]: p for p in m["parts"]}["env"]["truncated"])
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
                self.assertIn(B.command_prefix(self.home), text)

    # ------------------------------------------------------------ cards
    def test_open_cards(self):
        for tid in ('a-old','b-mid','c-new'):
            card=taskcard.new_card(self.st,tid,id=tid)
            taskcard.add_criterion(self.st,card,'確認する条件','pytest -q')
        text,m=self.build()
        self.assertIn('c-new',text)
        self.assertIn('b-mid',text)
        self.assertNotIn('a-old',text)
        self.assertIn('kiseki-da task show c-new',text)
        self.assertIn('未達',text)
        self.assertLessEqual(m['parts'][2]['tokens'],400)
        card.status='done'
        taskcard.save(self.st,card,['status:done'])
        text,m=self.build()
        self.assertNotIn('c-new',text)
        self.assertIn('a-old',text)

    def test_cards_part_token_limit(self):
        for tid in ('first','second'):
            card=taskcard.new_card(self.st,'長い目標。'*500,id=tid)
            for _ in range(8):
                taskcard.add_criterion(self.st,card,'長い確認内容。'*80,'pytest -q')
        text,m=self.build()
        self.assertIn('kiseki-da task show first',text)
        self.assertIn('kiseki-da task show second',text)
        self.assertLessEqual(m['parts'][2]['tokens'],400)
        self.assertIn('省略',text)

    def test_unreadable_cards_are_skipped(self):
        card=taskcard.new_card(self.st,'生きている作業',id='alive')
        self.st.task_path('bad').write_bytes(b'\xff\xfe')
        text,m=self.build()
        self.assertIn('alive',text)
        self.assertNotIn('bad',text)
        self.assertLessEqual(m['used'],2500)

    # ------------------------------------------------------------ character cap
    def test_chars_never_exceed_9000(self):
        card=taskcard.new_card(self.st,'x'*12000,id='long-goal')
        text,m=self.build()
        self.assertLessEqual(len(text),9000)
        self.assertIn('long-goal',text)
        self.assertIn('kiseki-da task show long-goal',text)
        self.assertEqual(m['chars'],len(text))

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
