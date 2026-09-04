"""test_store.py — TOML round trip, seq, snapshot, validate, sid rule, approve --supersedes (INTERFACES §10)."""
from __future__ import annotations

import contextlib
import datetime as dt
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import tomllib
import unittest
from pathlib import Path
from unittest import mock

from core.ctx import store as S
from core.ctx.store import Store, UserError

FX = Path(__file__).resolve().parent / "fixtures"


class StoreTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = (Path(self.tmp.name) / "pa").resolve()
        self.st = Store(home=self.home, sid="s-test")
        self.st.init()

    # ------------------------------------------------------------ helpers
    def test_helpers(self):
        self.assertEqual(S.estimate_tokens("abcd"), 1)
        self.assertEqual(S.estimate_tokens("あいうえおかきく"), 5)  # 8 / 1.6
        self.assertEqual(S.estimate_tokens(""), 0)
        self.assertEqual(S.redact("export API_KEY=abc123 && run"), "export [REDACTED] && run")
        self.assertEqual(S.redact("token: xyz"), "[REDACTED]")
        self.assertEqual(S.redact("Authorization: Bearer abcdefghijklmnop"), "Authorization: [REDACTED]")
        self.assertEqual(S.redact("run --token abcdefghijklmnop now"), "run [REDACTED] now")
        self.assertEqual(S.redact("https://user:password@example.invalid/path"), "[REDACTED]")
        self.assertEqual(S.redact("key sk-abcdefghijklmnop"), "key [REDACTED]")
        self.assertEqual(S.redact("no secrets here"), "no secrets here")
        self.assertEqual(S.dumps({"d": dt.date(2026, 9, 4), "s": "あ"}), '{"d": "2026-09-04", "s": "あ"}')
        self.assertEqual(S.parse_event_id("ev:s-1:12"), ("s-1", 12))
        self.assertEqual(S.parse_event_id("ev:a:b:3"), ("a:b", 3))
        self.assertIsNone(S.parse_event_id("last"))
        self.assertTrue(S.now_iso().endswith(("+09:00", "Z")) or "+" in S.now_iso() or "-" in S.now_iso()[10:])

    def test_kiseki_da_home_reads_env_each_call_and_pa_home_is_only_a_signal(self):
        old = os.environ.get("KISEKI_DA_HOME")
        old_pa = os.environ.get("PA_HOME")
        try:
            os.environ["KISEKI_DA_HOME"] = str(self.home)
            self.assertEqual(S.pa_home(), self.home.resolve())
            os.environ["KISEKI_DA_HOME"] = str(self.home / "other")
            self.assertEqual(S.pa_home(), (self.home / "other").resolve())
            os.environ["PA_HOME"] = str(self.home / "legacy")
            self.assertEqual(S.pa_home(), (self.home / "other").resolve())
            self.assertEqual(S.legacy_home_signal(), (self.home / "legacy").resolve())
        finally:
            if old is None:
                os.environ.pop("KISEKI_DA_HOME", None)
            else:
                os.environ["KISEKI_DA_HOME"] = old
            if old_pa is None:
                os.environ.pop("PA_HOME", None)
            else:
                os.environ["PA_HOME"] = old_pa

    # ------------------------------------------------------------ init
    def test_init_layout_and_force(self):
        for sub in ("tasks", "archive", "snapshots", "session"):
            self.assertTrue((self.home / sub).is_dir(), sub)
        self.assertTrue(self.st.profile_path.is_file())
        if os.name != "nt":
            self.assertEqual(stat.S_IMODE(self.home.stat().st_mode), 0o700)
        with self.assertRaises(UserError):
            self.st.init()
        created = self.st.init(force=True)
        self.assertIn(self.st.profile_path, created)
        self.assertEqual(len(list((self.home / "snapshots").glob("profile-*.toml"))), 1)

    # ------------------------------------------------------------ TOML
    def test_toml_roundtrip_fixture(self):
        shutil.copy(FX / "profile.sample.toml", self.st.profile_path)
        first = self.st.read_profile()
        self.assertEqual(len(first["constraints"]), 2)
        self.assertIsInstance(first["constraints"][0]["recorded_at"], dt.date)
        self.st.write_profile(first)
        second = self.st.read_profile()
        self.assertEqual(first, second)
        text = self.st.profile_path.read_text(encoding="utf-8")
        self.assertIn("[[constraints]]", text)
        self.assertIn("recorded_at = 2026-08-01", text)
        self.assertIn('languages = ["ja", "en"]', text)
        # emitter output is itself the canonical fixture form
        self.assertEqual(text, (FX / "profile.sample.toml").read_text(encoding="utf-8"))

    def test_toml_empty_sections(self):
        prof = self.st.read_profile()  # state.example: no item sections
        self.assertEqual([prof[s] for s in S.SECTIONS], [[], [], [], []])
        self.st.write_profile(prof)
        text = self.st.profile_path.read_text(encoding="utf-8")
        self.assertNotIn("[[", text)
        again = self.st.read_profile()
        self.assertEqual(again, prof)
        self.assertEqual(again["identity"]["timezone"], "Asia/Tokyo")

    def test_toml_escaping_and_types(self):
        prof = self.st.read_profile()
        prof["identity"]["name"] = 'say "hi"\\ \t tab\nnewline \x01'
        prof["identity"]["languages"] = []
        prof["facts"] = [{"id": "f1", "text": "x", "source": "user-stated", "recorded_at": dt.date(2026, 9, 4),
                          "confidence": 0.5, "review_by": dt.date(2027, 9, 4), "flag": True,
                          "when": dt.datetime(2026, 9, 4, 10, 0, tzinfo=dt.timezone.utc), "n": 3}]
        self.st.write_profile(prof)
        back = self.st.read_profile()
        self.assertEqual(back["identity"]["name"], prof["identity"]["name"])
        self.assertEqual(back["identity"]["languages"], [])
        f = back["facts"][0]
        self.assertIs(f["flag"], True)
        self.assertEqual(f["n"], 3)
        self.assertEqual(f["confidence"], 0.5)
        self.assertEqual(f["when"], dt.datetime(2026, 9, 4, 10, 0, tzinfo=dt.timezone.utc))
        nested = S.emit_toml({"a": {"numbers": [1, 2], "nested": {"x": 1}}})
        self.assertEqual(tomllib.loads(nested), {"a": {"numbers": [1, 2], "nested": {"x": 1}}})
        with self.assertRaises(TypeError):
            S.emit_toml({"unsupported": object()})

    def test_toml_naive_datetime_is_local_time(self):
        """A TOML local date-time (naive datetime) hand-edited into profile.toml is emitted as local time,
        the same convention parse_ts uses, instead of surfacing as an internal error (exit 2)."""
        naive = dt.datetime(2026, 9, 4, 10, 0)
        self.assertEqual(S._toml_value(naive), naive.astimezone().isoformat())
        with open(self.st.profile_path, "a", encoding="utf-8") as f:
            f.write('\n[[facts]]\nid = "f1"\ntext = "x"\nsource = "user-stated"\n'
                    'recorded_at = 2026-09-04T10:00:00\nreview_by = 2027-01-01\n')
        self.assertEqual(self.st.remember("テスト2"), "p1")
        back = self.st.read_profile()
        self.assertEqual(back["facts"][0]["recorded_at"], naive.astimezone())
        self.assertEqual(back["preferences"][0]["id"], "p1")
        self.assertIn("recorded_at = 2026-09-04T10:00:00", self.st.profile_path.read_text(encoding="utf-8"))

    def test_read_profile_missing_file(self):
        self.st.profile_path.unlink()
        prof = self.st.read_profile()
        self.assertEqual(prof["constraints"], [])
        self.assertEqual(prof["schema"], 1)

    # ------------------------------------------------------------ events
    def test_seq_monotonic_and_ids(self):
        ids = [self.st.append_event({"type": "capture", "text": f"t{i}", "source": None, "url": None})
               for i in range(3)]
        self.assertEqual(ids, ["ev:s-test:1", "ev:s-test:2", "ev:s-test:3"])
        other = Store(home=self.home, sid="s-other")
        self.assertEqual(other.append_event({"type": "capture", "text": "o", "source": None, "url": None}),
                         "ev:s-other:1")
        self.assertEqual(self.st.append_event({"type": "capture", "text": "x", "source": None, "url": None}),
                         "ev:s-test:4")
        seqs = [ev["seq"] for ev in self.st.iter_events(sid="s-test")]
        self.assertEqual(seqs, [1, 2, 3, 4])
        rec = json.loads(self.st.events_path.read_text(encoding="utf-8").splitlines()[0])
        self.assertEqual(list(rec)[:4], ["ts", "sid", "seq", "type"])

    def test_append_event_concurrent_processes_unique_seq(self):
        """Parallel tool calls fire concurrent post-tool hooks for one session: seq must stay unique
        (ev:<sid>:<seq> is an id). N processes wait on a barrier file, then append together."""
        n_proc, per = 6, 20
        go = Path(self.tmp.name) / "go"
        script = (
            "import sys, time, pathlib; sys.path.insert(0, sys.argv[1])\n"
            "from core.ctx.store import Store\n"
            "st = Store(home=sys.argv[2], sid='s-conc'); go = pathlib.Path(sys.argv[3])\n"
            "while not go.exists(): time.sleep(0.005)\n"
            "for i in range(int(sys.argv[4])):\n"
            "    st.append_event({'type': 'capture', 'text': 'c%d' % i, 'source': None, 'url': None})\n"
        )
        procs = [subprocess.Popen([sys.executable, "-c", script, str(S.REPO_ROOT), str(self.home), str(go), str(per)])
                 for _ in range(n_proc)]
        time.sleep(0.3)  # let the interpreters reach the barrier so the appends overlap
        go.write_text("go", encoding="utf-8")
        self.assertEqual([p.wait(timeout=60) for p in procs], [0] * n_proc)
        seqs = sorted(ev["seq"] for ev in self.st.iter_events(sid="s-conc"))
        self.assertEqual(seqs, list(range(1, n_proc * per + 1)))
        self.assertEqual((self.home / "session" / "s-conc.seq").read_text(encoding="utf-8").strip(), str(n_proc * per))
        self.assertEqual(self.st.append_event({"type": "capture", "sid": "s-conc", "text": "z"}),
                         f"ev:s-conc:{n_proc * per + 1}")

    def test_append_event_sid_rule(self):
        self.assertEqual(self.st.append_event({"type": "capture", "sid": "explicit", "text": "a"}), "ev:explicit:1")
        self.assertEqual(self.st.append_event({"type": "capture", "text": "b"}), "ev:s-test:1")
        anon = Store(home=self.home)
        self.assertEqual(anon.append_event({"type": "capture", "text": "c"}), "ev:nosession:1")
        anon.set_current_sid("s-current")
        self.assertEqual(anon.effective_sid(), "s-current")
        self.assertEqual(anon.append_event({"type": "capture", "text": "d"}), "ev:s-current:1")
        self.assertEqual(self.st.effective_sid(), "s-test")  # explicit sid wins over current
        anon.clear_current_sid()
        self.assertIsNone(anon.current_sid())
        self.assertEqual(anon.effective_sid(), "nosession")
        ev = self.st.append_event({"type": "capture", "text": "e", "ts": "2020-01-01T00:00:00+09:00"})
        self.assertEqual(self.st.event_by_id(ev)["ts"], "2020-01-01T00:00:00+09:00")

    def test_multiple_active_sessions_require_explicit_sid(self):
        anon = Store(home=self.home)
        anon.set_current_sid("claude-a")
        anon.set_current_sid("codex-b")
        self.assertEqual(set(anon.active_sids()), {"claude-a", "codex-b"})
        with self.assertRaisesRegex(UserError, "--sid"):
            anon.effective_sid()
        self.assertEqual(Store(home=self.home, sid="claude-a").effective_sid(), "claude-a")

    def test_clearing_one_session_restores_unambiguous_current(self):
        anon = Store(home=self.home)
        anon.set_current_sid("claude-a")
        anon.set_current_sid("codex-b")
        anon.clear_current_sid("claude-a")
        self.assertEqual(anon.active_sids(), ["codex-b"])
        self.assertEqual(anon.current_sid(), "codex-b")

    def test_append_event_unknown_type(self):
        with self.assertRaises(ValueError):
            self.st.append_event({"type": "bogus"})

    def test_iter_and_lookup(self):
        shutil.copy(FX / "events.sample.jsonl", self.st.events_path)
        self.assertEqual(len(list(self.st.iter_events())), 14)
        self.assertEqual([e["seq"] for e in self.st.iter_events(types={"tool_call"})], [6, 7, 8])
        self.assertEqual(list(self.st.iter_events(sid="nope")), [])
        self.assertEqual(list(self.st.iter_events(since_days=1)), [])  # fixture is dated 2026-09-03
        self.assertEqual(len(list(self.st.iter_events(since_days=100000))), 14)
        ev = self.st.event_by_id("ev:s-fx-1:8")
        self.assertEqual(ev["tool"], "Read")
        self.assertIsNone(self.st.event_by_id("ev:s-fx-1:99"))
        self.assertIsNone(self.st.event_by_id("garbage"))
        self.assertEqual(self.st.last_event(types={"tool_call"})["seq"], 8)
        self.assertEqual(self.st.last_event(types={"tool_call"}, tool="bash")["seq"], 7)
        self.assertEqual(self.st.last_event(types={"tool_call"}, sid="s-fx-1", tool="Read")["seq"], 8)
        self.assertIsNone(self.st.last_event(types={"tool_call"}, sid="other"))
        # broken lines are skipped
        with open(self.st.events_path, "a", encoding="utf-8") as f:
            f.write("{not json\n\n")
        self.assertEqual(len(list(self.st.iter_events())), 14)

    # ------------------------------------------------------------ snapshot
    def test_snapshot_keeps_latest_30(self):
        paths = [self.st.snapshot() for _ in range(33)]
        self.assertEqual(len(set(paths)), 33)
        left = sorted((self.home / "snapshots").glob("profile-*.toml"))
        self.assertEqual(len(left), 30)
        self.assertEqual(left[-1], paths[-1])
        self.st.profile_path.unlink()
        with self.assertRaises(UserError):
            self.st.snapshot()

    def test_write_profile_snapshots_and_validates(self):
        prof = self.st.read_profile()
        self.st.write_profile(prof)
        self.assertEqual(len(list((self.home / "snapshots").glob("profile-*.toml"))), 1)
        prof["constraints"] = [{"id": "c1", "text": "x"}]  # hand-edited minimal item: only id / text are 必須 (§1)
        self.st.write_profile(prof)
        self.assertEqual(self.st.read_profile()["constraints"], [{"id": "c1", "text": "x"}])
        self.assertEqual(len(list((self.home / "snapshots").glob("profile-*.toml"))), 2)
        prof["constraints"] = [{"id": "c1"}]
        with self.assertRaises(UserError):
            self.st.write_profile(prof)
        self.assertEqual(len(list((self.home / "snapshots").glob("profile-*.toml"))), 2)
        self.assertEqual(self.st.remember("手書き項目があっても書ける"), "p1")

    # ------------------------------------------------------------ validate
    def test_cli_log_checks_common_keys(self):
        """`ctx log` validates ts / sid before appending (A-17): exit 1 with one Japanese line, nothing written."""
        from core.ctx import cli

        def run(data: str) -> tuple[int, str, str]:
            out, err = io.StringIO(), io.StringIO()
            with mock.patch.dict(os.environ, {"KISEKI_DA_HOME": str(self.home)}), \
                    contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = cli.main(["log", "error", "--data", data, "--sid", "s-test"])
            return rc, out.getvalue(), err.getvalue()

        for data in ('{"sid": 123}', '{"ts": 5, "where": "w"}', '{"ts": "garbage"}', '{"sid": ["a"]}', '{"ts": true}'):
            rc, out, err = run(data)
            self.assertEqual((rc, out), (1, ""), data)
            self.assertTrue(err.startswith("--data が不正です: "), (data, err))
            self.assertEqual(err.count("\n"), 1, err)
            self.assertNotIn("内部エラー", err)
        self.assertEqual(list(self.st.iter_events()), [])
        rc, out, err = run('{"ts": "2020-01-01T10:00:00+09:00", "sid": "s-other", "seq": 99, "where": "w", '
                           '"text": "token=abc"}')
        self.assertEqual((rc, out, err), (0, "ev:s-other:1\n", ""))
        rc, out, err = run('{"ts": null, "sid": "", "where": "w"}')  # null / empty = default, as in append_event
        self.assertEqual((rc, out, err), (0, "ev:s-test:1\n", ""))
        evs = list(self.st.iter_events())
        self.assertEqual([self.st.validate("event", e) for e in evs], [[], []])
        self.assertEqual((evs[0]["ts"], evs[0]["sid"], evs[0]["seq"], evs[0]["type"], evs[0]["text"]),
                         ("2020-01-01T10:00:00+09:00", "s-other", 1, "error", "[REDACTED]"))
        self.assertEqual((evs[1]["sid"], evs[1]["seq"]), ("s-test", 1))
        self.assertIsNotNone(S.parse_ts(evs[1]["ts"]))

    def test_validate(self):
        ok_item = {"id": "c1", "text": "t", "source": "user-stated", "recorded_at": dt.date(2026, 9, 4),
                   "confidence": 1.0, "review_by": dt.date(2027, 3, 3)}
        prof = {"schema": 1, "identity": {}, "da": {}, "constraints": [ok_item]}
        self.assertEqual(self.st.validate("profile", prof), [])
        bad = {"schema": "1", "identity": {}, "constraints": [{"id": 1, "text": "t"}]}
        errs = self.st.validate("profile", bad)
        self.assertTrue(any(e.startswith("schema") for e in errs))
        self.assertTrue(any(e.startswith("da") for e in errs))
        self.assertTrue(any(e.startswith("constraints[0].id") for e in errs))
        self.assertFalse(any(e.startswith("constraints[0].source") for e in errs))  # not 必須 (INTERFACES §1)
        minimal = {"schema": 1, "identity": {}, "da": {}, "constraints": [{"id": "c1", "text": "t"}]}
        self.assertEqual(self.st.validate("profile", minimal), [])
        typed = dict(ok_item, source=5, recorded_at=20260904, review_by=dt.time(1, 2), confidence="high")
        errs = self.st.validate("profile", {"schema": 1, "identity": {}, "da": {}, "facts": [typed]})
        self.assertEqual(sorted(e.split(":")[0] for e in errs),
                         ["facts[0].confidence", "facts[0].recorded_at", "facts[0].review_by", "facts[0].source"])
        # unknown enum values pass
        weird = dict(ok_item, source="whatever", status="zzz")
        self.assertEqual(self.st.validate("profile", {"schema": 1, "identity": {}, "da": {}, "goals": [weird]}), [])
        self.assertEqual(self.st.validate("event", {"ts": "t", "sid": "s", "seq": 1, "type": "anything"}), [])
        self.assertTrue(self.st.validate("event", {"ts": "t", "sid": "s", "seq": "1", "type": "x"}))
        self.assertTrue(self.st.validate("event", {"ts": "t", "sid": "s", "type": "x"}))
        cand = {"id": "cand-1", "kind": "preference", "text": "t", "source": "inference", "status": "pending",
                "created": "2026-09-04T00:00:00+09:00"}
        self.assertEqual(self.st.validate("candidate", cand), [])
        self.assertTrue(self.st.validate("candidate", {"id": "cand-1"}))
        task = {"id": "t", "status": "open", "risk": "R1", "kind": "code", "created": "c", "updated": "u",
                "budget": {}, "goal": "g", "criteria": [{"id": "C1", "claim": "a", "check": "b",
                                                        "evidence": "-", "status": "open"}],
                "constraints": [], "assumptions": [], "questions": [], "decisions": [], "log": []}
        self.assertEqual(self.st.validate("task", task), [])
        task["criteria"].append({"id": "C2"})
        self.assertTrue(any(e.startswith("criteria[1].claim") for e in self.st.validate("task", task)))
        self.assertTrue(self.st.validate("task", "not a dict"))

    # ------------------------------------------------------------ candidates
    def test_candidates_dedup_and_status(self):
        c1 = self.st.append_candidate({"text": "日時は ISO 8601", "quote": "今後は ISO 8601 で", "source": "user-stated"})
        self.assertEqual(c1, "cand-1")
        self.assertEqual(self.st.append_candidate({"text": " 日時は ISO 8601 ", "source": "user-stated"}), "cand-1")
        c2 = self.st.append_candidate({"text": "B", "kind": "constraint", "source": "inference", "key": "k"})
        self.assertEqual(c2, "cand-2")
        recs = self.st.candidates()
        self.assertEqual([r["id"] for r in recs], ["cand-1", "cand-2"])
        self.assertEqual(recs[0]["status"], "pending")
        self.assertEqual(recs[0]["quote"], "今後は ISO 8601 で")
        self.assertEqual(recs[1]["key"], "k")
        self.assertEqual(recs[1]["sid"], "s-test")
        self.assertEqual([e["type"] for e in self.st.iter_events()], ["candidate", "candidate"])
        self.st.set_candidate_status("cand-2", "rejected", "no")
        self.assertEqual(self.st.candidates("pending")[0]["id"], "cand-1")
        self.assertEqual(self.st.candidates("rejected")[0]["reason"], "no")
        # rejected text can be proposed again as a new pending candidate
        self.assertEqual(self.st.append_candidate({"text": "B", "source": "inference"}), "cand-3")
        with self.assertRaises(UserError):
            self.st.set_candidate_status("cand-99", "approved")
        with self.assertRaises(UserError):
            self.st.append_candidate({"text": "x", "kind": "mood"})
        with self.assertRaises(UserError):
            self.st.append_candidate({"text": "", "kind": "fact"})
        with self.assertRaises(UserError):
            self.st.append_candidate({"text": "x", "source": "guess"})
        cid = self.st.append_candidate({"text": "password: hunter2 で入る", "source": "user-stated"})
        self.assertNotIn("hunter2", self.st.candidates()[-1]["text"])
        self.assertEqual(cid, "cand-4")

    # ------------------------------------------------------------ approve / reject
    def test_approve_defaults(self):
        c_user = self.st.append_candidate({"text": "A", "source": "user-stated", "kind": "preference"})
        c_inf = self.st.append_candidate({"text": "B", "source": "inference", "kind": "constraint"})
        c_doc = self.st.append_candidate({"text": "C", "source": "document:repo:x/README", "kind": "fact"})
        c_goal = self.st.append_candidate({"text": "D", "source": "user-stated", "kind": "goal"})
        self.assertEqual(self.st.approve(c_user), "p1")
        self.assertEqual(self.st.approve(c_inf), "c1")
        self.assertEqual(self.st.approve(c_doc, confidence=0.5, review_by="2030-01-02"), "f1")
        self.assertEqual(self.st.approve(c_goal), "g1")
        prof = self.st.read_profile()
        p1, c1, f1, g1 = prof["preferences"][0], prof["constraints"][0], prof["facts"][0], prof["goals"][0]
        self.assertEqual((p1["source"], p1["confidence"]), ("user-stated", 1.0))
        self.assertEqual((c1["source"], c1["confidence"]), ("approved-inference", 0.7))
        self.assertEqual((f1["source"], f1["confidence"], f1["review_by"]),
                         ("document:repo:x/README", 0.5, dt.date(2030, 1, 2)))
        self.assertEqual(g1["status"], "active")
        td = dt.date.today()
        self.assertEqual(p1["recorded_at"], td)
        self.assertEqual(p1["review_by"], td + dt.timedelta(days=180))
        self.assertEqual(c1["review_by"], td + dt.timedelta(days=180))
        self.assertEqual(g1["review_by"], td + dt.timedelta(days=90))
        self.assertEqual({r["id"]: r["status"] for r in self.st.candidates()},
                         {c_user: "approved", c_inf: "approved", c_doc: "approved", c_goal: "approved"})
        approvals = [e for e in self.st.iter_events(types={"approval"})]
        self.assertEqual([(a["cid"], a["pid"], a["action"]) for a in approvals],
                         [(c_user, "p1", "approve"), (c_inf, "c1", "approve"), (c_doc, "f1", "approve"),
                          (c_goal, "g1", "approve")])
        self.assertEqual(len(list((self.home / "snapshots").glob("profile-*.toml"))), 4)
        with self.assertRaises(UserError):
            self.st.approve(c_user)  # not pending any more
        with self.assertRaises(UserError):
            self.st.approve("cand-99")
        c_bad = self.st.append_candidate({"text": "E", "source": "user-stated"})
        with self.assertRaises(UserError):
            self.st.approve(c_bad, confidence=1.5)
        with self.assertRaises(UserError):
            self.st.approve(c_bad, review_by="tomorrow")
        self.assertEqual(self.st.candidates("pending")[0]["id"], c_bad)  # nothing written on failure
        self.assertEqual(self.st.new_profile_id("preferences"), "p2")

    def test_approve_supersedes_archives_and_corrects(self):
        shutil.copy(FX / "profile.sample.toml", self.st.profile_path)
        cid = self.st.append_candidate({"text": "コミットメッセージは英語で書く（本文も英語）",
                                        "quote": "コミットは全部英語で", "source": "user-stated"})
        pid = self.st.approve(cid, supersedes="p2")
        self.assertEqual(pid, "p6")
        prof = self.st.read_profile()
        ids = [p["id"] for p in prof["preferences"]]
        self.assertNotIn("p2", ids)
        self.assertIn("p6", ids)
        new = next(p for p in prof["preferences"] if p["id"] == "p6")
        self.assertEqual(new["corrected_from"], "p2")
        self.assertEqual(new["key"], "commit-lang")
        arch = [json.loads(l) for l in self.st.archive_path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(arch), 1)
        self.assertEqual((arch[0]["id"], arch[0]["superseded_by"], arch[0]["section"]), ("p2", "p6", "preferences"))
        self.assertEqual(arch[0]["recorded_at"], "2026-08-20")
        corr = list(self.st.iter_events(types={"correction"}))
        self.assertEqual(len(corr), 1)
        self.assertEqual(corr[0]["before"], "コミットメッセージは日本語で書く")
        self.assertEqual(corr[0]["after"], "コミットメッセージは英語で書く（本文も英語）")
        self.assertEqual(corr[0]["quote"], "コミットは全部英語で")
        self.assertEqual([e["type"] for e in self.st.iter_events()][-2:], ["correction", "approval"])
        # archived ids are never reused
        self.assertEqual(self.st.new_profile_id("preferences"), "p7")
        with self.assertRaises(UserError):
            self.st.approve(self.st.append_candidate({"text": "Z", "source": "user-stated"}), supersedes="p2")

    def test_approve_supersedes_failed_write_leaves_archive_untouched(self):
        """write_profile is the only validate / atomic gate: when it refuses (hand-edited item), the archive
        must not claim the old item retired, the candidate stays pending and no event is written."""
        shutil.copy(FX / "profile.sample.toml", self.st.profile_path)
        with open(self.st.profile_path, "a", encoding="utf-8") as f:
            f.write('\n[[facts]]\nid = 7\ntext = "壊れた項目"\n')
        cid = self.st.append_candidate({"text": "Z", "source": "user-stated"})
        before = list(self.st.iter_events())
        with self.assertRaises(UserError) as cm:
            self.st.approve(cid, supersedes="p2")
        self.assertIn("facts[1].id", str(cm.exception))
        self.assertFalse(self.st.archive_path.exists())
        self.assertIn("p2", [p["id"] for p in self.st.read_profile()["preferences"]])
        self.assertEqual(self.st.candidates()[0]["status"], "pending")
        self.assertEqual(list(self.st.iter_events()), before)
        shutil.copy(FX / "profile.sample.toml", self.st.profile_path)  # user fixes the profile and retries
        self.assertEqual(self.st.approve(cid, supersedes="p2"), "p6")
        arch = [json.loads(l) for l in self.st.archive_path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual([(a["id"], a["superseded_by"]) for a in arch], [("p2", "p6")])
        self.assertEqual([e["type"] for e in self.st.iter_events()][len(before):], ["correction", "approval"])

    def test_reject(self):
        cid = self.st.append_candidate({"text": "A", "source": "inference"})
        self.st.reject(cid, reason="違う")
        rec = self.st.candidates()[0]
        self.assertEqual((rec["status"], rec["reason"]), ("rejected", "違う"))
        ev = list(self.st.iter_events(types={"approval"}))[-1]
        self.assertEqual((ev["cid"], ev["pid"], ev["action"]), (cid, None, "reject"))
        with self.assertRaises(UserError):
            self.st.reject(cid)

    # ------------------------------------------------------------ text / tasks
    def test_writes_before_init_create_private_home(self):
        """A hook may run before `ctx init` (fail-open). The home it creates is the private area (mode 700)."""
        if os.name == "nt":
            self.skipTest("POSIX mode bits are not a Windows ACL assertion")
        old = os.umask(0o022)
        try:
            base = Path(self.tmp.name)
            Store(home=base / "h1", sid="s").append_event({"type": "guard", "tool": "Bash", "decision": "allow",
                                                           "reason": "", "target": "ls"})
            Store(home=base / "h2").set_current_sid("s-x")
            Store(home=base / "h3", sid="s").append_candidate({"text": "x", "source": "user-stated"})
            Store(home=base / "h4", sid="s").remember("y")
            Store(home=base / "h5" / "nested").write_text("tasks/t.md", "id: t\n")
            for name in ("h1", "h2", "h3", "h4", "h5/nested"):
                self.assertEqual(stat.S_IMODE((base / name).stat().st_mode), 0o700, name)
            self.assertTrue((base / "h1" / "events.jsonl").is_file())
            self.assertEqual((base / "h2" / "session" / "current").read_text(encoding="utf-8"), "s-x\n")
            existing = base / "h6"
            existing.mkdir()
            os.chmod(existing, 0o755)
            Store(home=existing, sid="s").append_event({"type": "capture", "text": "t", "source": None, "url": None})
            self.assertEqual(stat.S_IMODE(existing.stat().st_mode), 0o755)  # init is the fix-up point
        finally:
            os.umask(old)

    def test_text_and_tasks(self):
        self.assertIsNone(self.st.read_text("tasks/nope.md"))
        self.st.write_text("tasks/a.md", "id: a\n")
        self.st.write_text("tasks/b.md", "id: b\n")
        self.assertEqual(self.st.read_text("tasks/a.md"), "id: a\n")
        self.assertEqual(self.st.list_tasks(), ["a", "b"])
        self.assertEqual(self.st.task_path("a"), self.home / "tasks" / "a.md")
        self.assertEqual([p.name for p in (self.home / "tasks").iterdir() if p.name.endswith(".tmp")], [])

    # ------------------------------------------------------------ remember / capture (P2)
    def test_remember_writes_profile_directly(self):
        pid = self.st.remember("日時は ISO 8601 で統一", kind="preference", key="datetime-format")
        self.assertEqual(pid, "p1")
        item = self.st.read_profile()["preferences"][0]
        self.assertEqual((item["source"], item["confidence"], item["key"]), ("user-stated", 1.0, "datetime-format"))
        self.assertEqual(item["review_by"], dt.date.today() + dt.timedelta(days=180))
        self.assertEqual(self.st.remember("10 月に v1", kind="goal"), "g1")
        self.assertEqual(self.st.read_profile()["goals"][0]["status"], "active")
        ev = list(self.st.iter_events(types={"approval"}))
        self.assertEqual([(e["cid"], e["pid"], e["action"]) for e in ev], [(None, "p1", "approve"), (None, "g1", "approve")])
        self.assertEqual(self.st.candidates(), [])
        with self.assertRaises(UserError):
            self.st.remember("   ")
        with self.assertRaises(UserError):
            self.st.remember("x", kind="mood")

    def test_capture(self):
        ev_id = self.st.capture("GitHub Actions の runner は 24.04")
        ev = self.st.event_by_id(ev_id)
        self.assertEqual((ev["type"], ev["source"], ev["url"]), ("capture", None, None))
        ev2 = self.st.event_by_id(self.st.capture("https://example.com/runners"))
        self.assertEqual((ev2["source"], ev2["url"]), ("document:https://example.com/runners", "https://example.com/runners"))
        ev3 = self.st.event_by_id(self.st.capture("https://example.com/x", source="document:notes"))
        self.assertEqual(ev3["source"], "document:notes")
        ev4 = self.st.event_by_id(self.st.capture("token=abc123 を見た", source="user"))
        self.assertNotIn("abc123", ev4["text"])
        ev5 = self.st.event_by_id(self.st.capture("https://example.com/a see this"))
        self.assertEqual((ev5["text"], ev5["url"], ev5["source"]),
                         ("https://example.com/a see this", "https://example.com/a", "document:https://example.com/a"))
        ev6 = self.st.event_by_id(self.st.capture("see https://example.com/a"))
        self.assertEqual((ev6["url"], ev6["source"]), (None, None))
        with self.assertRaises(UserError):
            self.st.capture("")


class ReportTestCase(unittest.TestCase):
    """report.week() lives here to keep the test-file count at the 52-file plan (INTERFACES §10)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = (Path(self.tmp.name) / "pa").resolve()
        self.st = Store(home=self.home, sid="s-r")
        self.st.init()

    def test_week_keys_and_zero_defaults(self):
        from core.ctx import report
        d = report.week(self.st)
        self.assertEqual(tuple(d), report.WEEK_KEYS)
        self.assertEqual(sum(1 for v in d.values() if v), 0)
        self.assertEqual(len(list(self.st.iter_events())), 0)  # no side effects

    def test_week_counts(self):
        from core.ctx import report
        from core.ctx import taskcard
        shutil.copy(FX / "profile.sample.toml", self.st.profile_path)
        st = self.st
        st.append_event({"type": "session_start", "env": "claude-code", "source": "startup"})
        st.append_event({"type": "context_manifest", "budget": 2500, "used": 1000, "parts": [], "conflicts": [], "chars": 10})
        st.append_event({"type": "context_manifest", "budget": 2500, "used": 2000, "parts": [], "conflicts": [], "chars": 10})
        card = taskcard.new_card(st, "Add refresh", risk="R1", id="t1")
        st.append_event({"type": "question", "task": "t1", "text": "q1"})
        st.append_event({"type": "assumption", "task": "t1", "text": "a1"})
        st.append_event({"type": "question", "task": "t2", "text": "q2"})  # no follow-up for t2 → not useful
        st.append_event({"type": "correction", "before": "a", "after": "b", "quote": "c"})
        card.criteria.append(taskcard.Criterion("C1", "claim", "pytest x", "ev:s-r:1", "open"))
        card.criteria.append(taskcard.Criterion("C2", "claim", "pytest y", "-", "open"))
        taskcard.save(st, card, ["criterion:C2"])
        st.append_event({"type": "gate", "task": "t1", "blocked": True, "reason": "r"})
        st.append_event({"type": "gate", "task": "t2", "blocked": True, "reason": "r"})
        st.append_event({"type": "task_update", "task": "t1", "risk": "R1", "status": "deferred", "changed": ["defer"]})
        st.append_event({"type": "gate", "task": None, "blocked": False, "reason": ""})
        st.append_event({"type": "guard", "tool": "Bash", "decision": "deny", "reason": "r", "target": "rm -rf /"})
        st.append_event({"type": "guard", "tool": "Bash", "decision": "ask", "reason": "r", "target": "deploy"})
        st.append_event({"type": "guard", "tool": "Bash", "decision": "allow", "reason": "", "target": "ls"})
        st.append_event({"type": "worker_dispatch", "task": "t1", "role": "research", "tokens_est": 100})
        st.append_event({"type": "search", "query": "x", "k": 5, "hits": ["ev:s-r:1", "ev:s-r:2", "profile:c1"]})
        st.append_event({"type": "evidence", "task": "t1", "criterion": "C1", "ref": "ev:s-r:1"})
        c1 = st.append_candidate({"text": "A", "source": "user-stated"})
        c2 = st.append_candidate({"text": "B", "source": "user-stated"})
        st.append_candidate({"text": "C", "source": "user-stated"})
        st.approve(c1)
        st.reject(c2)
        st.remember("direct")
        st.append_event({"type": "task_close", "task": "t9", "risk": "R1", "status": "done"})
        st.append_event({"type": "session_start", "env": "codex", "source": None, "ts": "2020-01-01T00:00:00+09:00"})
        d = report.week(st)
        self.assertEqual(d["sessions"], 1)              # the 2020 one is outside the window
        self.assertEqual(d["resident_tokens_avg"], 1500.0)
        self.assertEqual(d["questions"], 2)
        self.assertEqual(d["questions_useful_ratio"], 0.5)
        self.assertEqual(d["assumptions"], 1)
        self.assertEqual(d["corrections"], 1)
        self.assertEqual(d["cards_open"], 1)
        self.assertEqual(d["cards_closed"], 1)
        self.assertEqual(d["evidence_fill_ratio"], 0.5)
        self.assertEqual(d["gate_blocks"], 2)
        self.assertEqual(d["gate_overrides"], 0.5)
        self.assertEqual((d["guard_deny"], d["guard_ask"]), (1, 1))
        self.assertEqual(d["workers"], 1)
        self.assertEqual((d["candidates_pending"], d["candidates_approved"], d["candidates_rejected"]), (1, 1, 1))
        self.assertEqual(d["stale_items"], 1)
        self.assertEqual(d["searches"], 1)
        self.assertEqual(d["search_cited_ratio"], 0.5)

    def test_week_skips_unreadable_card(self):
        """One non-UTF-8 card (hand-saved as Shift-JIS) is skipped, all keys still come out (INTERFACES §8; same guard as build/search/gate)."""
        from core.ctx import report
        from core.ctx import taskcard
        taskcard.new_card(self.st, "ok card", risk="R1", id="ok")
        self.st.task_path("bad").write_bytes(b"id: bad\nstatus: open\nrisk: R1\n\n# Goal\n\x93\xfa\x96\x7b\x8c\xea\n")
        d = report.week(self.st)
        self.assertEqual(tuple(d), report.WEEK_KEYS)
        self.assertEqual(d["cards_open"], 1)

    def test_week_skips_non_dict_profile_items(self):
        """A hand-written `constraints = ["a"]` (list of str) is skipped; stale_items still counts dict items (same guard as build/search)."""
        from core.ctx import report
        self.st.profile_path.write_text(
            'schema = 1\nconstraints = ["a"]\n[identity]\nname = ""\n[da]\nname = ""\n'
            '[[preferences]]\nid = "p1"\ntext = "x"\nsource = "user-stated"\nrecorded_at = 2026-01-01\n'
            'confidence = 1.0\nreview_by = 2026-01-31\n', encoding="utf-8")
        d = report.week(self.st)
        self.assertEqual(tuple(d), report.WEEK_KEYS)
        self.assertEqual(d["stale_items"], 1)

    # ------------------------------------------------------------ audit (P3)
    def _home_snapshot(self) -> tuple[list[str], bytes | None]:
        paths = sorted(p.relative_to(self.home).as_posix() for p in self.home.rglob("*"))
        events = self.st.events_path.read_bytes() if self.st.events_path.exists() else None
        return paths, events

    def test_audit_keys_and_types_on_empty_store(self):
        from core.ctx import report
        before = self._home_snapshot()
        d = report.audit(self.st)
        self.assertEqual(tuple(d), report.AUDIT_KEYS)
        self.assertIsInstance(d["file_count"], int)
        self.assertEqual(d["hooks_never_fired"], ["session-start", "pre-tool", "post-tool", "stop", "session-end"])
        self.assertIsInstance(d["event_types_without_writer"], list)
        self.assertEqual(d["profile_items_never_hit"], [])   # state.example has no items
        self.assertEqual(d["duplicate_profile_texts"], [])
        self.assertIsInstance(d["policy_lines"], int)
        self.assertIsInstance(d["policy_tokens"], int)
        json.loads(S.dumps(d))   # JSON-serialisable (--json prints the dict itself)
        self.assertEqual(self._home_snapshot(), before)   # no event, no file under PA_HOME

    def test_audit_file_count_and_writers_match_test_limits(self):
        from core.ctx import report
        from core.tests import test_limits
        d = report.audit(self.st)
        self.assertEqual(d["file_count"], len(test_limits.counted_files()))
        self.assertEqual(report._counted_files(), test_limits.counted_files())
        self.assertEqual(d["event_types_without_writer"], [])   # CHECKLIST A5 on this repository
        self.assertEqual(d["event_types_without_writer"], test_limits.event_types_without_writer())

    def test_audit_policy_numbers(self):
        from core.ctx import report
        text = (S.REPO_ROOT / "core" / "policy" / "interaction.md").read_text(encoding="utf-8")
        d = report.audit(self.st)
        self.assertEqual((d["policy_lines"], d["policy_tokens"]), (len(text.splitlines()), S.estimate_tokens(text)))
        self.assertLessEqual(d["policy_lines"], 60)
        self.assertLessEqual(d["policy_tokens"], 800)

    def test_audit_hooks_never_fired_uses_30_day_window(self):
        from core.ctx import report
        st = self.st
        old = (dt.datetime.now().astimezone() - dt.timedelta(days=31)).isoformat(timespec="seconds")
        st.append_event({"type": "guard", "tool": "Bash", "decision": "allow", "reason": "", "target": "ls", "ts": old})
        st.append_event({"type": "session_end", "reason": "other", "candidates_created": 0, "ts": "garbage"})
        # 31 days old and an unreadable ts both fall outside the window (judged by ts, as in week())
        self.assertEqual(report.audit(st)["hooks_never_fired"],
                         ["session-start", "pre-tool", "post-tool", "stop", "session-end"])
        st.append_event({"type": "guard", "tool": "Bash", "decision": "allow", "reason": "", "target": "ls"})
        self.assertEqual(report.audit(st)["hooks_never_fired"], ["session-start", "post-tool", "stop", "session-end"])
        st.append_event({"type": "session_start", "env": "claude-code", "source": "startup"})
        st.append_event({"type": "tool_call", "tool": "Bash", "target": "ls", "ok": True, "out_len": 0, "out_hash": "e3b0c44298fc"})
        st.append_event({"type": "gate", "task": None, "blocked": False, "reason": ""})
        self.assertEqual(report.audit(st)["hooks_never_fired"], ["session-end"])
        st.append_event({"type": "session_end", "reason": "other", "candidates_created": 0})
        before = self._home_snapshot()
        self.assertEqual(report.audit(st)["hooks_never_fired"], [])
        self.assertEqual(self._home_snapshot(), before)   # audit wrote no event and no file

    def test_audit_profile_hits_and_duplicates(self):
        from core.ctx import report
        st = self.st
        prof = st.read_profile()
        prof["constraints"] = [{"id": "c1", "text": "日時は ISO 8601 で書く"}, {"id": "c2", "text": " 日時は ISO 8601 で書く "}]
        prof["preferences"] = [{"id": "p1", "text": "unique"}, {"id": "p2", "text": "unique"}, {"id": "p3", "text": "other"}]
        prof["facts"] = [{"id": "f1", "text": "日時は ISO 8601 で書く"}]
        st.write_profile(prof)
        d = report.audit(st)
        self.assertEqual(d["profile_items_never_hit"], ["c1", "c2", "f1", "p1", "p2", "p3"])
        self.assertEqual(d["duplicate_profile_texts"], [
            {"text": "日時は ISO 8601 で書く", "ids": ["c1", "c2", "f1"]},   # first occurrence first, stripped exact match
            {"text": "unique", "ids": ["p1", "p2"]},
        ])
        st.append_event({"type": "search", "query": "x", "k": 5, "hits": ["profile:c1", "ev:s-r:1", "profile:zz", 3]})
        st.append_event({"type": "search", "query": "y", "k": 5, "hits": ["profile:p3"],
                         "ts": "2020-01-01T00:00:00+09:00"})   # outside the 30-day window
        st.append_event({"type": "search", "query": "z", "k": 5, "hits": None})
        d = report.audit(st)
        self.assertEqual(d["profile_items_never_hit"], ["c2", "f1", "p1", "p2", "p3"])
        # non-dict items and items without a str id are skipped, as in build/search/week
        st.profile_path.write_text(
            'schema = 1\nconstraints = ["a"]\n[identity]\nname = ""\n[da]\nname = ""\n'
            '[[preferences]]\nid = "p1"\ntext = "x"\n[[facts]]\nid = 7\ntext = "x"\n', encoding="utf-8")
        d = report.audit(st)
        self.assertEqual((d["profile_items_never_hit"], d["duplicate_profile_texts"]), (["p1"], []))
        st.profile_path.unlink()
        d = report.audit(st)   # no profile.toml → empty profile (DECISIONS), every key still present
        self.assertEqual(tuple(d), report.AUDIT_KEYS)
        self.assertEqual((d["profile_items_never_hit"], d["duplicate_profile_texts"]), ([], []))

    def test_audit_cli(self):
        from core.ctx import cli, report
        for argv in (["report", "--audit", "--json"], ["report", "--json", "--audit"]):
            out, err = io.StringIO(), io.StringIO()
            with mock.patch.dict(os.environ, {"KISEKI_DA_HOME": str(self.home)}), \
                    contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = cli.main(argv)
            self.assertEqual((rc, err.getvalue()), (0, ""), argv)
            data = json.loads(out.getvalue())
            self.assertIsInstance(data, dict)
            self.assertEqual(tuple(data), report.AUDIT_KEYS)
            expected = report.audit(self.st)
            self.assertIsInstance(data["file_count"], int)   # compared loosely: other builders may add files meanwhile
            self.assertEqual({k: v for k, v in data.items() if k != "file_count"},
                             {k: v for k, v in expected.items() if k != "file_count"})
        out = io.StringIO()
        with mock.patch.dict(os.environ, {"KISEKI_DA_HOME": str(self.home)}), contextlib.redirect_stdout(out):
            rc = cli.main(["report", "--audit"])
        self.assertEqual(rc, 0)
        lines = out.getvalue().splitlines()
        self.assertEqual([ln.split(":")[0] for ln in lines], list(report.AUDIT_KEYS))
        self.assertTrue(lines[1].startswith('hooks_never_fired: ["session-start"'), lines[1])   # lists via dumps
        self.assertEqual(list(self.st.iter_events()), [])   # the CLI wrote nothing either


if __name__ == "__main__":
    unittest.main()
