"""test_search.py — tokenizer, BM25 ranking, decay, kinds / since filters, snippets, search event (INTERFACES §7, §10)."""
from __future__ import annotations

import contextlib
import datetime as dt
import io
import os
import tempfile
import unittest
from pathlib import Path

from core.ctx import search as S
from core.ctx import store as ST
from core.ctx import taskcard
from core.ctx.store import Store

FX = Path(__file__).resolve().parent / "fixtures"


def _ts(days_ago: float) -> str:
    return (dt.datetime.now().astimezone() - dt.timedelta(days=days_ago)).isoformat(timespec="seconds")


class SearchTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = (Path(self.tmp.name) / "pa").resolve()
        self._old_home = os.environ.get("KISEKI_DA_HOME")
        os.environ["KISEKI_DA_HOME"] = str(self.home)
        self.addCleanup(self._restore_env)
        self.st = Store(home=self.home, sid="s-test")
        self.st.init()

    def _restore_env(self):
        if self._old_home is None:
            os.environ.pop("KISEKI_DA_HOME", None)
        else:
            os.environ["KISEKI_DA_HOME"] = self._old_home

    # ------------------------------------------------------------ helpers
    def use_profile_fixture(self):
        self.st.write_text("profile.toml", (FX / "profile.sample.toml").read_text(encoding="utf-8"))

    def event(self, type_: str, days_ago: float = 0.0, **fields) -> str:
        ev = {"type": type_, "ts": _ts(days_ago)}
        ev.update(fields)  # an explicit ts= in fields wins
        return self.st.append_event(ev)

    def capture(self, text: str, days_ago: float = 0.0, **fields) -> str:
        return self.event("capture", days_ago, text=text, source=None, url=None, **fields)

    @staticmethod
    def ids(hits: list[dict]) -> list[str]:
        return [h["id"] for h in hits]

    # ------------------------------------------------------------ tokenize
    def test_tokenize_mixed_japanese_bigrams_and_english(self):
        self.assertEqual(S.tokenize("ISO 8601 で統一"), ["iso", "8601", "で統", "統一"])
        self.assertEqual(S.tokenize("日時のフォーマット"),
                         ["日時", "時の", "のフ", "フォ", "ォー", "ーマ", "マッ", "ット"])
        self.assertEqual(S.tokenize("snake_case Value42"), ["snake_case", "value42"])
        self.assertEqual(S.tokenize("ｻｰﾊﾞｰ"), ["ｻｰ", "ｰﾊ", "ﾊﾞ", "ﾞｰ"])

    def test_tokenize_single_cjk_char(self):
        self.assertEqual(S.tokenize("旧 API"), ["旧", "api"])
        self.assertEqual(S.tokenize("あ"), ["あ"])
        self.assertEqual(S.tokenize("東京、大阪"), ["東京", "大阪"])  # punctuation splits CJK runs

    def test_tokenize_ignores_punctuation_and_single_ascii(self):
        self.assertEqual(S.tokenize("Hello, world! a b c"), ["hello", "world"])
        self.assertEqual(S.tokenize("、。！？…（）-/"), [])
        self.assertEqual(S.tokenize(""), [])
        self.assertEqual(S.tokenize("   \n\t"), [])

    # ------------------------------------------------------------ ranking
    def test_mixed_query_hits_capture_not_unrelated(self):
        ts = _ts(0)
        hit_id = self.capture("日時のフォーマットは ISO 8601 で統一する", ts=ts)
        self.capture("コミットメッセージは英語で書く")
        hits = S.search(self.st, "ISO 8601 で統一")
        self.assertEqual(self.ids(hits), [hit_id])
        self.assertEqual(hit_id, "ev:s-test:1")
        h = hits[0]
        self.assertEqual(h["kind"], "capture")
        self.assertEqual(h["source"], "capture")
        self.assertEqual(h["date"], ts[:10])
        self.assertFalse(h["stale"])
        self.assertGreater(h["score"], 0)
        self.assertEqual(h["snippet"], "日時のフォーマットは ISO 8601 で統一する")

    def test_time_decay_orders_newer_first(self):
        text = "検索の減衰テスト decay"
        old = self.capture(text, days_ago=205)
        new = self.capture(text, days_ago=5)
        hits = S.search(self.st, "decay", since_days=365)
        self.assertEqual(self.ids(hits), [new, old])
        self.assertGreater(hits[0]["score"], hits[1]["score"])
        # 200 days apart → ratio 0.5 ** (200 / 90) (half-life 90 days)
        self.assertAlmostEqual(hits[1]["score"] / hits[0]["score"], 0.5 ** (200 / 90), delta=0.02)
        flat = S.search(self.st, "decay", since_days=365, decay=False)
        self.assertEqual(self.ids(flat), [new, old])  # tie → newer date first
        self.assertEqual(flat[0]["score"], flat[1]["score"])

    def test_correction_outranks_identical_assumption(self):
        ts = _ts(3)
        before, after = "更新間隔は 60 分", "更新間隔は 15 分"
        assum = self.event("assumption", ts=ts, task="t1", text=f"{before} {after}")
        corr = self.event("correction", ts=ts, before=before, after=after, quote="15 分にして")
        hits = S.search(self.st, "更新間隔")
        self.assertEqual(self.ids(hits), [corr, assum])
        self.assertEqual([h["source"] for h in hits], ["correction", "assumption"])
        self.assertEqual({h["kind"] for h in hits}, {"events"})
        self.assertAlmostEqual(hits[0]["score"], 1.2 * hits[1]["score"], delta=1e-3)

    def test_kind_weights_capture_over_events(self):
        ts = _ts(2)
        cap = self.capture("weightcheck の比較", ts=ts)
        prop = self.event("proposal", ts=ts, text="weightcheck の比較", evidence_counts={}, kill_condition="-")
        hits = S.search(self.st, "weightcheck")
        self.assertEqual(self.ids(hits), [cap, prop])
        self.assertAlmostEqual(hits[0]["score"] / hits[1]["score"], 0.9 / 0.7, delta=1e-2)

    def test_tie_break_by_id_when_score_and_date_equal(self):
        ts = _ts(1)
        a = self.capture("tiebreak 文書", ts=ts)
        b = self.capture("tiebreak 文書", ts=ts)
        hits = S.search(self.st, "tiebreak")
        self.assertEqual(self.ids(hits), sorted([a, b]))
        self.assertEqual(hits[0]["score"], hits[1]["score"])

    # ------------------------------------------------------------ profile
    def test_profile_hit_and_stale_marker(self):
        self.use_profile_fixture()
        hits = S.search(self.st, "本番 DB")
        self.assertEqual(self.ids(hits), ["profile:c1"])
        h = hits[0]
        self.assertEqual(h["kind"], "profile")
        self.assertEqual(h["source"], "user-stated")
        self.assertEqual(h["date"], "2026-08-01")
        self.assertFalse(h["stale"])
        self.assertEqual(h["snippet"], "本番 DB への直接書込は禁止。マイグレーション経由のみ")
        hits = S.search(self.st, "旧 API")
        self.assertEqual(self.ids(hits), ["profile:c2"])
        self.assertTrue(hits[0]["stale"])
        self.assertEqual(hits[0]["date"], "2026-01-05")

    def test_profile_all_sections_indexed_with_item_source(self):
        self.use_profile_fixture()
        hits = S.search(self.st, "GitHub Actions")
        self.assertEqual(set(self.ids(hits)), {"profile:g2", "profile:f1"})  # done goal + fact
        by_id = {h["id"]: h for h in hits}
        self.assertEqual(by_id["profile:f1"]["source"], "document:repo:X/.github/workflows/ci.yml")
        self.assertEqual(by_id["profile:g2"]["source"], "user-stated")
        p3 = S.search(self.st, "結論を先に")
        self.assertEqual(self.ids(p3), ["profile:p3"])
        self.assertEqual(p3[0]["source"], "approved-inference")

    def test_profile_missing_review_by_is_not_stale(self):
        self.st.write_text("profile.toml", "\n".join([
            'schema = 1', '[identity]', 'name = ""', '[da]', 'name = ""', '',
            '[[facts]]', 'id = "f1"', 'text = "noreview テスト"', 'source = "user-stated"',
            'recorded_at = 2026-08-01', 'confidence = 1.0', '',
        ]))
        hits = S.search(self.st, "noreview")
        self.assertEqual(self.ids(hits), ["profile:f1"])
        self.assertFalse(hits[0]["stale"])

    def test_cli_prints_stale_marker(self):
        from core.ctx import cli
        self.use_profile_fixture()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli.main(["search", "旧 API", "--sid", "s-test"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("[profile] 2026-01-05 user-stated(profile:c2) [stale]\n3 月末までは旧 API v1 を使う", out)

    # ------------------------------------------------------------ small corpora
    def test_single_document_corpus_still_hits(self):
        only = self.capture("lonely document について")
        hits = S.search(self.st, "lonely")
        self.assertEqual(self.ids(hits), [only])
        self.assertGreater(hits[0]["score"], 0)

    def test_term_in_every_document_still_hits_all(self):
        a = self.capture("shared 語 one")
        b = self.capture("shared 語 two")
        hits = S.search(self.st, "shared")
        self.assertEqual(set(self.ids(hits)), {a, b})
        self.assertTrue(all(h["score"] > 0 for h in hits))

    # ------------------------------------------------------------ filters and limits
    def test_kinds_filter(self):
        self.use_profile_fixture()
        cap = self.capture("本番 DB のバックアップを取った")
        q = self.event("question", task="t1", text="本番 DB は誰が管理していますか")
        self.assertEqual(set(self.ids(S.search(self.st, "本番 DB"))), {"profile:c1", cap, q})
        self.assertEqual(self.ids(S.search(self.st, "本番 DB", kinds=["profile"])), ["profile:c1"])
        self.assertEqual(self.ids(S.search(self.st, "本番 DB", kinds=["capture"])), [cap])
        self.assertEqual(self.ids(S.search(self.st, "本番 DB", kinds=["events"])), [q])
        self.assertEqual(set(self.ids(S.search(self.st, "本番 DB", kinds=["events", "capture"]))), {cap, q})
        self.assertEqual(S.search(self.st, "本番 DB", kinds=["tasks"]), [])

    def test_k_limit(self):
        for i in range(7):
            self.capture(f"klimit 文書 {i}")
        self.assertEqual(len(S.search(self.st, "klimit")), 5)
        self.assertEqual(len(S.search(self.st, "klimit", k=2)), 2)
        self.assertEqual(len(S.search(self.st, "klimit", k=100)), 7)
        self.assertEqual(S.search(self.st, "klimit", k=0), [])

    def test_since_days_applies_to_events_only(self):
        self.use_profile_fixture()
        old = self.capture("本番 DB の移行メモ", days_ago=400)
        taskcard.new_card(self.st, "本番 DB の移行手順を書く", risk="R1", kind="ops", id="db-migration")
        recent = set(self.ids(S.search(self.st, "本番 DB", since_days=180, decay=False)))
        self.assertEqual(recent, {"profile:c1", "task:db-migration"})  # task_open is not indexed either
        wide = set(self.ids(S.search(self.st, "本番 DB", since_days=1000, decay=False)))
        self.assertEqual(wide, {"profile:c1", "task:db-migration", old})
        unbounded = set(self.ids(S.search(self.st, "本番 DB", since_days=None, decay=False)))
        self.assertEqual(unbounded, wide)

    # ------------------------------------------------------------ tasks and events
    def test_task_card_indexed_without_log(self):
        card = taskcard.new_card(self.st, "Implement widget caching for the dashboard", id="widget-cache")
        card.log.append("2026-09-04T10:00:00+09:00 note: zebra note")
        taskcard.save(self.st, card, ["note"])
        hits = S.search(self.st, "widget")
        self.assertEqual(self.ids(hits), ["task:widget-cache"])
        h = hits[0]
        self.assertEqual(h["kind"], "tasks")
        self.assertEqual(h["source"], "task")
        self.assertEqual(h["date"], card.updated[:10])
        self.assertFalse(h["stale"])
        self.assertIn("# Goal", h["snippet"])
        self.assertIn("Implement widget caching", h["snippet"])
        self.assertNotIn("# Log", h["snippet"])
        self.assertNotIn("zebra", h["snippet"])
        self.assertEqual(S.search(self.st, "zebra"), [])

    def test_event_types_indexed_and_excluded(self):
        q = self.event("question", task="t1", text="qword はどうしますか")
        a = self.event("assumption", task="t1", text="aword と仮定する")
        w = self.event("worker_return", task="t1", role="research", tokens_est=10, text="wword の調査結果")
        p = self.event("proposal", text="pword を提案する", evidence_counts={}, kill_condition="-")
        self.event("tool_call", tool="Bash", target="echo xword", ok=True, out_len=0,
                   out_hash="e3b0c44298fc", text="xword")
        self.event("task_open", task="t1", risk="R1", kind="code", goal="yword を作る", text="yword")
        self.event("task_update", task="t1", risk="R1", status="open", changed=["note"], text="zword")
        self.event("task_close", task="t1", risk="R1", status="done", text="vword")
        for word, ev_id, src in (("qword", q, "question"), ("aword", a, "assumption"),
                                 ("wword", w, "worker_return"), ("pword", p, "proposal")):
            hits = S.search(self.st, word)
            self.assertEqual(self.ids(hits), [ev_id], word)
            self.assertEqual(hits[0]["kind"], "events", word)
            self.assertEqual(hits[0]["source"], src, word)
        for word in ("xword", "yword", "zword", "vword"):
            self.assertEqual(S.search(self.st, word), [], word)

    # ------------------------------------------------------------ search event
    def test_search_event_records_hits_in_order(self):
        a = self.capture("evlog alpha")
        b = self.capture("evlog beta", days_ago=30)
        hits = S.search(self.st, "evlog", k=3)
        self.assertEqual(self.ids(hits), [a, b])
        ev = self.st.last_event(types={"search"})
        self.assertIsNotNone(ev)
        self.assertEqual(ev["query"], "evlog")
        self.assertEqual(ev["k"], 3)
        self.assertEqual(ev["hits"], [a, b])
        self.assertEqual(ev["sid"], "s-test")

    def test_empty_query_returns_nothing_but_writes_event(self):
        self.capture("something")
        self.assertEqual(S.search(self.st, ""), [])
        ev = self.st.last_event(types={"search"})
        self.assertEqual((ev["query"], ev["k"], ev["hits"]), ("", 5, []))
        self.assertEqual(S.search(self.st, "、。 a", k=2), [])  # no tokens at all
        ev = self.st.last_event(types={"search"})
        self.assertEqual((ev["query"], ev["k"], ev["hits"]), ("、。 a", 2, []))

    # ------------------------------------------------------------ hit shape and snippet
    def test_hit_keys_and_snippet_limit(self):
        long_text = "longcapture " + "とても長い本文です。" * 400  # ≈ 2,500 tokens
        ev_id = self.capture(long_text)
        hits = S.search(self.st, "longcapture")
        self.assertEqual(self.ids(hits), [ev_id])
        h = hits[0]
        self.assertEqual(set(h), {"id", "kind", "date", "source", "stale", "score", "snippet"})
        self.assertIsInstance(h["score"], float)
        self.assertIsInstance(h["stale"], bool)
        self.assertLessEqual(ST.estimate_tokens(h["snippet"]), 300)
        self.assertGreater(ST.estimate_tokens(h["snippet"]), 250)  # the cut does not collapse to the first word
        self.assertTrue(h["snippet"].startswith("longcapture とても"))
        self.assertTrue(h["snippet"].endswith("…"))

    def test_snippet_cuts_at_whitespace_boundary(self):
        words = " ".join(f"word{i:04d}" for i in range(400))  # ≈ 900 tokens, ASCII only
        ev_id = self.capture(words)
        hits = S.search(self.st, "word0001")
        self.assertEqual(self.ids(hits), [ev_id])
        snippet = hits[0]["snippet"]
        self.assertLessEqual(ST.estimate_tokens(snippet), 300)
        self.assertTrue(snippet.endswith("…"))
        body = snippet[:-1]
        self.assertFalse(body.endswith(" "))
        self.assertTrue(all(len(w) == 8 for w in body.split(" ")), body[-30:])  # no word was split


if __name__ == "__main__":
    unittest.main()
