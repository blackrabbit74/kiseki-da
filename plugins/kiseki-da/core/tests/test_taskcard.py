"""test_taskcard.py — parse/render round trip, check_evidence branches, close/defer, `last` resolution,
set_evidence events, brief (INTERFACES §10)."""
from __future__ import annotations

import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from core.ctx import store as S
from core.ctx import taskcard as T
from core.ctx.store import Store, UserError

FX = Path(__file__).resolve().parent / "fixtures"
SAMPLE_ID = "2026-09-03-auth-refresh"


class TaskcardTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name).resolve()
        self.st = Store(home=self.home, sid="s-test")
        self.st.init()

    # ------------------------------------------------------------ helpers
    def events(self, types: set[str] | None = None) -> list[dict]:
        return list(self.st.iter_events(types=types))

    def tool_call(self, tool: str, target: str, ok=True, sid: str | None = None) -> str:
        ev = {"type": "tool_call", "tool": tool, "target": target, "ok": ok, "out_len": 0,
              "out_hash": "e3b0c44298fc"}
        if sid:
            ev["sid"] = sid
        return self.st.append_event(ev)

    def card(self, risk: str = "R1", goal: str = "認証トークンの自動更新を追加する", **kw) -> T.TaskCard:
        return T.new_card(self.st, goal, risk=risk, **kw)

    def snapshot(self, card: T.TaskCard) -> tuple[bytes, bytes]:
        """(card file, events.jsonl) bytes — for the write-nothing assertions."""
        return self.st.task_path(card.id).read_bytes(), self.st.events_path.read_bytes()


# ---------------------------------------------------------------- parse / render

class ParseRenderTests(unittest.TestCase):
    def test_fixture_round_trip(self):
        text = (FX / "task.sample.md").read_text(encoding="utf-8")
        card = T.parse(text)
        self.assertEqual(card.id, SAMPLE_ID)
        self.assertEqual((card.status, card.risk, card.kind), ("open", "R1", "code"))
        self.assertEqual(card.budget, T.DEFAULT_BUDGET)
        self.assertEqual([c.id for c in card.criteria], ["C1", "C2", "C3"])
        self.assertEqual(card.criteria[0].evidence, "ev:s-fx-1:6")
        self.assertEqual(card.criteria[1].evidence, "-")
        self.assertEqual(card.criteria[2].status, "pass")
        self.assertEqual(len(card.log), 1)
        self.assertEqual(T.render(card), text)

    def test_pipe_in_claim_and_empty_lists(self):
        card = T.TaskCard(id="t-1", status="open", risk="R1", kind="code",
                          created="2026-09-04T10:00:00+09:00", updated="2026-09-04T10:00:00+09:00",
                          budget=dict(T.DEFAULT_BUDGET), goal="a | b を直す",
                          criteria=[T.Criterion("C1", "x | y が通る", "pytest -q | tail")])
        text = T.render(card)
        self.assertIn("x \\| y", text)
        for title in T.SECTION_TITLES:
            self.assertIn(f"# {title}", text)  # empty sections keep their heading
        self.assertEqual(T.parse(text), card)


class NewCardGoalTests(TaskcardTestCase):
    def test_multiline_goal_round_trips(self):
        goal = "ログインを直す\n\n- 手順 1\n#notes は見出しではない\n  # 字下げも見出しではない"
        card = self.card(goal=goal)
        self.assertEqual(card.goal, goal)
        self.assertEqual(T.load(self.st, card.id).goal, goal)

    def test_goal_with_heading_line_is_rejected(self):
        """A `# ` line would be read back as a section heading (§5), moving or dropping the rest of the goal."""
        for goal in ("Fix login\n# Log\nsecret", "# Goal\nx", "a\n# Notes\nmore", "  # Log"):
            with self.assertRaises(UserError, msg=goal) as cm:
                T.new_card(self.st, goal, risk="R1")
            self.assertIn("「# 」で始まる行", str(cm.exception))
        self.assertEqual(self.st.list_tasks(), [])
        self.assertEqual(self.events({"task_open"}), [])


class IdValidationTests(TaskcardTestCase):
    """show/set/close/defer/brief pass a raw positional id; load/save must keep it inside $PA_HOME/tasks."""

    def test_load_and_save_reject_ids_outside_the_namespace(self):
        for bad in ("../victim", "A", "-x", "a/b", "a.b", "", "a" * 65):
            with self.assertRaises(UserError, msg=bad):
                T.load(self.st, bad)
            card = T.TaskCard(id=bad, status="open", risk="R1", kind="code", created="", updated="",
                              budget={}, goal="x")
            with self.assertRaises(UserError, msg=bad):
                T.save(self.st, card, ["note"])
        self.assertEqual(self.st.list_tasks(), [])
        self.assertEqual(self.events({"task_update"}), [])

    def test_traversal_id_cannot_read_or_overwrite_outside_home(self):
        from core.ctx import cli
        home = Path(self.tmp.name) / "home"
        st = Store(home=home, sid="s-test")
        st.init()
        victim = Path(self.tmp.name) / "victim.md"
        original = "title: hello\n\nsome text\n"
        victim.write_text(original, encoding="utf-8")
        argvs = (["task", "show", "../victim"],
                 ["task", "set", "../victim", "--note", "clobbered"],
                 ["task", "close", "../victim"],
                 ["task", "defer", "../victim", "--reason", "x"],
                 ["task", "brief", "../victim", "--role", "research"])
        with mock.patch.dict(os.environ, {"KISEKI_DA_HOME": str(home)}):
            for argv in argvs:
                out, err = io.StringIO(), io.StringIO()
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    rc = cli.main(argv)
                self.assertEqual((rc, out.getvalue()), (1, ""), argv)
                self.assertEqual(err.getvalue().count("\n"), 1, argv)
                self.assertIn("カード id が不正です", err.getvalue(), argv)
        self.assertEqual(victim.read_text(encoding="utf-8"), original)
        self.assertEqual(st.list_tasks(), [])
        self.assertEqual(list(st.iter_events(types={"task_update", "task_close", "worker_dispatch"})), [])

    def test_list_cards_skips_files_outside_the_id_namespace(self):
        card = self.card()
        self.st.write_text("tasks/Not An Id.md", T.render(card))
        self.assertEqual([c.id for c in T.list_cards(self.st)], [card.id])


# ---------------------------------------------------------------- check_evidence

class CheckEvidenceTests(TaskcardTestCase):
    def setUp(self):
        super().setUp()
        shutil.copy(FX / "events.sample.jsonl", self.st.events_path)

    def check(self, evidence: str, check: str):
        return T.check_evidence(self.st, T.Criterion("C1", "claim", check, evidence, "open"))

    def test_no_evidence(self):
        self.assertEqual(self.check("-", "pytest -q"), "no evidence")
        self.assertEqual(self.check("", "pytest -q"), "no evidence")
        self.assertEqual(self.check(" ", "pytest -q"), "no evidence")

    def test_evidence_not_found(self):
        self.assertEqual(self.check("ev:s-fx-1:99", "pytest -q"), "evidence not found")
        self.assertEqual(self.check("ev:nope:1", "pytest -q"), "evidence not found")
        self.assertEqual(self.check("garbage", "pytest -q"), "evidence not found")

    def test_not_a_tool_call(self):
        self.assertEqual(self.check("ev:s-fx-1:9", "Read x"), "not a tool call")  # capture
        self.assertEqual(self.check("ev:s-fx-1:3", "pytest -q"), "not a tool call")  # task_open

    def test_tool_heads(self):
        self.assertIsNone(self.check("ev:s-fx-1:8", "Read git diff"))  # Read tool_call
        self.assertIsNone(self.check("ev:s-fx-1:8", "read"))
        self.assertEqual(self.check("ev:s-fx-1:8", "grep foo"), "tool mismatch")
        self.assertEqual(self.check("ev:s-fx-1:6", "Read git diff"), "tool mismatch")  # Bash vs Read
        # a command-style check against a non-Bash tool is a command mismatch (no substring inference)
        self.assertEqual(self.check("ev:s-fx-1:8", "pytest git-diff"), "command mismatch")

    def test_command_heads(self):
        ev_id = self.tool_call("Bash", "pytest tests/x.py")
        self.assertIsNone(self.check(ev_id, "pytest tests/x.py -q"))
        self.assertIsNone(self.check(ev_id, "PYTEST"))
        self.assertEqual(self.check(ev_id, "npm test"), "command mismatch")
        self.assertEqual(self.check(ev_id, ""), "command mismatch")
        self.assertIsNone(self.check("ev:s-fx-1:6", "pytest tests/test_auth.py"))
        self.assertEqual(self.check("ev:s-fx-1:6", "tests/test_auth.py"), "command mismatch")  # never substring

    def test_command_failed_and_unknown_ok(self):
        self.assertEqual(self.check("ev:s-fx-1:7", "pytest tests/test_other.py -q"), "command failed")
        self.assertEqual(self.check("ev:s-fx-1:7", "npm test"), "command mismatch")  # mismatch wins over failed
        ev_id = self.tool_call("Bash", "pytest -q", ok=None)
        self.assertEqual(self.check(ev_id, "pytest -q"), "command failed")

    def test_missing_evidence_keeps_criterion_order(self):
        shutil.copy(FX / "task.sample.md", self.st.task_path(SAMPLE_ID))
        card = T.load(self.st, SAMPLE_ID)
        self.assertEqual([(c.id, r) for c, r in T.missing_evidence(self.st, card)], [("C2", "no evidence")])
        card.criteria[0].evidence = "ev:s-fx-1:7"
        self.assertEqual([(c.id, r) for c, r in T.missing_evidence(self.st, card)],
                         [("C1", "command failed"), ("C2", "no evidence")])


# ---------------------------------------------------------------- criteria / set / add

class CardEditTests(TaskcardTestCase):
    def test_add_criterion_numbering(self):
        card = self.card()
        c1 = T.add_criterion(self.st, card, "更新処理の単体テストが通る", "pytest tests/test_auth.py")
        self.assertEqual((c1.id, c1.evidence, c1.status), ("C1", "-", "open"))
        c2 = T.add_criterion(self.st, card, " 回帰がない ", " pytest -q ")
        self.assertEqual((c2.id, c2.claim, c2.check), ("C2", "回帰がない", "pytest -q"))
        card.criteria.remove(c1)  # removing a criterion never renumbers the rest
        self.assertEqual(T.add_criterion(self.st, card, "x", "y").id, "C3")
        self.assertEqual([c.id for c in T.load(self.st, card.id).criteria], ["C2", "C3"])
        ups = self.events({"task_update"})
        self.assertEqual([e["changed"] for e in ups], [["criterion:C1"], ["criterion:C2"], ["criterion:C3"]])
        self.assertEqual((ups[-1]["task"], ups[-1]["risk"], ups[-1]["status"]), (card.id, "R1", "open"))
        for claim, check in (("", "pytest"), ("x", ""), ("  ", " ")):
            with self.assertRaises(UserError):
                T.add_criterion(self.st, card, claim, check)
        self.assertEqual(len(self.events({"task_update"})), 3)

    def test_add_criterion_uses_max_suffix(self):
        card = self.card()
        card.criteria = [T.Criterion("C1", "a", "b"), T.Criterion("C5", "c", "d")]
        self.assertEqual(T.add_criterion(self.st, card, "e", "f").id, "C6")

    def test_set_status_and_risk(self):
        card = self.card()
        T.set_status(self.st, card, "deferred")
        T.set_risk(self.st, card, "R2")
        loaded = T.load(self.st, card.id)
        self.assertEqual((loaded.status, loaded.risk), ("deferred", "R2"))
        ups = self.events({"task_update"})
        self.assertEqual([e["changed"] for e in ups], [["status:deferred"], ["risk:R2"]])
        self.assertEqual((ups[-1]["status"], ups[-1]["risk"]), ("deferred", "R2"))
        with self.assertRaises(UserError):
            T.set_status(self.st, card, "closed")
        with self.assertRaises(UserError):
            T.set_risk(self.st, card, "R4")
        self.assertEqual(len(self.events({"task_update"})), 2)

    def test_assumption_question_decision_note(self):
        card = self.card()
        T.add_assumption(self.st, card, " 更新間隔は 15 分 token: abc ")
        T.add_question(self.st, card, "再試行回数は？")
        T.add_decision(self.st, card, "要求時に\n更新する")
        T.add_note(self.st, card, "テストを追加した")
        loaded = T.load(self.st, card.id)
        self.assertEqual(loaded.assumptions, ["更新間隔は 15 分 token: abc"])
        self.assertEqual(loaded.questions, ["再試行回数は？"])
        self.assertEqual(loaded.decisions, ["要求時に 更新する"])  # one bullet per item
        self.assertEqual(len(loaded.log), 1)
        ts, _, text = loaded.log[0].partition(" ")
        self.assertIsNotNone(S.parse_ts(ts))
        self.assertEqual(text, "テストを追加した")
        self.assertEqual([e["type"] for e in self.events()],
                         ["task_open", "task_update", "assumption", "task_update", "question",
                          "task_update", "task_update"])
        self.assertEqual([e["changed"] for e in self.events({"task_update"})],
                         [["assumption"], ["question"], ["decision"], ["note"]])
        a = self.events({"assumption"})[0]
        self.assertEqual((a["task"], a["text"]), (card.id, "更新間隔は 15 分 [REDACTED]"))
        q = self.events({"question"})[0]
        self.assertEqual((q["task"], q["text"]), (card.id, "再試行回数は？"))
        n = len(self.events())
        for fn in (T.add_assumption, T.add_question, T.add_decision, T.add_note):
            with self.assertRaises(UserError):
                fn(self.st, card, " \n ")
        self.assertEqual(len(self.events()), n)


# ---------------------------------------------------------------- set_evidence / last

class EvidenceTests(TaskcardTestCase):
    def test_last_prefers_effective_sid_then_falls_back(self):
        card = self.card()
        T.add_criterion(self.st, card, "a", "pytest -q")
        with self.assertRaises(UserError) as cm:
            T.set_evidence(self.st, card, "C1", "last")
        self.assertEqual(str(cm.exception), "参照できるツール証拠がありません")
        other = self.tool_call("Bash", "pytest -q", sid="s-other")
        self.assertEqual(other, "ev:s-other:1")
        self.assertEqual(T.set_evidence(self.st, card, "C1", "last"), other)  # no s-test tool_call → fallback
        mine = self.tool_call("Bash", "pytest -q")
        self.tool_call("Bash", "ls", sid="s-other")  # newer, but in another sid
        self.assertEqual(T.set_evidence(self.st, card, "C1", "last"), mine)
        self.assertEqual(T.load(self.st, card.id).criteria[0].evidence, mine)

    def test_last_tool_picks_latest_matching(self):
        card = self.card()
        T.add_criterion(self.st, card, "a", "Read git diff")
        self.tool_call("Read", "/repo/a.py")
        r2 = self.tool_call("Read", "/repo/b.py")
        b = self.tool_call("Bash", "git diff")
        self.assertEqual(T.set_evidence(self.st, card, "C1", "last:Read"), r2)
        self.assertEqual(T.set_evidence(self.st, card, "C1", "last:read"), r2)  # case-insensitive
        self.assertEqual(T.set_evidence(self.st, card, "C1", "last:bash"), b)
        self.assertEqual(T.set_evidence(self.st, card, "C1", "last"), b)
        with self.assertRaises(UserError) as cm:
            T.set_evidence(self.st, card, "C1", "last:Write")
        self.assertEqual(str(cm.exception), "参照できるツール証拠がありません")
        w = self.tool_call("Write", "/repo/c.py", sid="s-other")
        self.assertEqual(T.set_evidence(self.st, card, "C1", "last:Write"), w)  # fallback per tool

    def test_last_skips_unknown_status_wrapper_event(self):
        card = self.card()
        T.add_criterion(self.st, card, "a", "pytest -q")
        verified = self.tool_call("Bash", "pytest -q", ok=True)
        self.tool_call("Bash", "kiseki-da verify run -- pytest -q", ok=None)
        self.assertEqual(T.set_evidence(self.st, card, "C1", "last"), verified)

    def test_set_evidence_writes_task_update_and_evidence(self):
        card = self.card()
        T.add_criterion(self.st, card, "a", "pytest -q")
        ev_id = self.tool_call("Bash", "pytest -q")
        n = len(self.events())
        self.assertEqual(T.set_evidence(self.st, card, "C1", ev_id), ev_id)
        evs = self.events()[n:]
        self.assertEqual([e["type"] for e in evs], ["task_update", "evidence"])
        self.assertEqual((evs[0]["task"], evs[0]["changed"]), (card.id, ["evidence:C1"]))
        self.assertEqual({k: evs[1][k] for k in ("task", "criterion", "ref")},
                         {"task": card.id, "criterion": "C1", "ref": ev_id})
        loaded = T.load(self.st, card.id)
        self.assertEqual((loaded.criteria[0].evidence, loaded.criteria[0].status), (ev_id, "open"))

    def test_set_evidence_errors_write_nothing(self):
        card = self.card()
        T.add_criterion(self.st, card, "a", "pytest -q")
        self.tool_call("Bash", "pytest -q")
        before = self.snapshot(card)
        for ref in ("ev:s-test:99", "ev:nope:1", "foo", "last:", ""):
            with self.assertRaises(UserError):
                T.set_evidence(self.st, card, "C1", ref)
        with self.assertRaises(UserError) as cm:
            T.set_evidence(self.st, card, "C9", "last")
        self.assertEqual(str(cm.exception), "完了条件がありません: C9")
        self.assertEqual(self.snapshot(card), before)
        # any existing event id is accepted here; check_evidence judges it at close time
        cap = self.st.append_event({"type": "capture", "text": "x", "source": None, "url": None})
        self.assertEqual(T.set_evidence(self.st, card, "C1", cap), cap)
        self.assertEqual(T.check_evidence(self.st, card.criteria[0]), "not a tool call")


# ---------------------------------------------------------------- close / defer

class CloseDeferTests(TaskcardTestCase):
    def test_verify_runner_records_only_real_exit_status(self):
        from core.ctx import cli
        with mock.patch.dict(os.environ, {"KISEKI_DA_HOME": str(self.home)}):
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = cli.main(["verify", "run", "--", sys.executable, "-c", "print('verified')"])
            self.assertEqual((rc, out.getvalue(), err.getvalue()), (0, "verified\n", ""))
            event = list(Store(home=self.home).iter_events(types={"tool_call"}))[-1]
            self.assertIs(event["ok"], True)
            criterion = T.Criterion("C1", "real command passed", event["target"],
                                    f"ev:{event['sid']}:{event['seq']}", "open")
            self.assertIsNone(T.check_evidence(Store(home=self.home), criterion))
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                rc = cli.main(["verify", "run", "--", sys.executable, "-c", "raise SystemExit(7)"])
            self.assertEqual(rc, 7)
            failed = list(Store(home=self.home).iter_events(types={"tool_call"}))[-1]
            self.assertIs(failed["ok"], False)

    def test_close_refused_writes_nothing(self):
        card = self.card()
        T.add_criterion(self.st, card, "更新処理の単体テストが通る", "pytest tests/test_auth.py")
        before = self.snapshot(card)
        self.assertEqual(T.close(self.st, card), ["C1: no evidence"])
        self.assertEqual(self.snapshot(card), before)
        self.assertEqual((card.status, card.criteria[0].status), ("open", "open"))
        T.add_criterion(self.st, card, "差分を読み返した", "Read git diff")
        self.tool_call("Bash", "pytest tests/test_auth.py -q")
        T.set_evidence(self.st, card, "C1", "last")
        card.criteria[1].evidence = "ev:s-test:99"
        before = self.snapshot(card)
        self.assertEqual(T.close(self.st, card), ["C2: evidence not found"])
        self.assertEqual(self.snapshot(card), before)

    def test_close_success(self):
        card = self.card()
        T.add_criterion(self.st, card, "単体テストが通る", "pytest tests/test_auth.py")
        T.add_criterion(self.st, card, "差分を読み返した", "Read git diff")
        self.tool_call("Bash", "pytest tests/test_auth.py -q")
        T.set_evidence(self.st, card, "C1", "last")
        self.tool_call("Read", "/repo/git-diff.txt")
        T.set_evidence(self.st, card, "C2", "last:Read")
        n = len(self.events())
        self.assertEqual(T.close(self.st, card), [])
        self.assertEqual(card.status, "done")
        self.assertEqual([c.status for c in card.criteria], ["pass", "pass"])
        loaded = T.load(self.st, card.id)
        self.assertEqual(loaded.status, "done")
        self.assertEqual([c.status for c in loaded.criteria], ["pass", "pass"])
        evs = self.events()[n:]
        self.assertEqual([e["type"] for e in evs], ["task_update", "task_close"])
        self.assertEqual((evs[0]["task"], evs[0]["status"], evs[0]["changed"]), (card.id, "done", ["status:done"]))
        self.assertEqual({k: evs[1][k] for k in ("task", "risk", "status")},
                         {"task": card.id, "risk": "R1", "status": "done"})

    def test_close_fixture_card_end_to_end(self):
        shutil.copy(FX / "events.sample.jsonl", self.st.events_path)
        shutil.copy(FX / "task.sample.md", self.st.task_path(SAMPLE_ID))
        card = T.load(self.st, SAMPLE_ID)
        self.assertEqual(T.close(self.st, card), ["C2: no evidence"])
        T.set_evidence(self.st, card, "C2", "ev:s-fx-1:7")  # failed pytest run
        self.assertEqual(T.close(self.st, card), ["C2: command failed"])
        self.tool_call("Bash", "pytest -q")
        T.set_evidence(self.st, card, "C2", "last")
        self.assertEqual(T.close(self.st, card), [])
        self.assertEqual(T.load(self.st, SAMPLE_ID).status, "done")

    def test_close_without_criteria(self):
        r1 = self.card()
        before = self.snapshot(r1)
        self.assertEqual(T.close(self.st, r1), ["-: no criteria"])
        self.assertEqual(self.snapshot(r1), before)
        r3 = self.card(risk="R3", goal="本番へデプロイする")
        self.assertEqual(T.close(self.st, r3), ["-: no criteria"])
        r0 = self.card(risk="R0", goal="ログを読んで答える")
        self.assertEqual(T.close(self.st, r0), [])
        self.assertEqual(T.load(self.st, r0.id).status, "done")
        self.assertEqual([(e["task"], e["risk"], e["status"]) for e in self.events({"task_close"})],
                         [(r0.id, "R0", "done")])

    def test_defer(self):
        card = self.card()
        T.add_criterion(self.st, card, "単体テストが通る", "pytest -q")
        T.add_criterion(self.st, card, "差分を読み返した", "Read git diff")
        card.criteria[0].status = "pass"
        n = len(self.events())
        with self.assertRaises(UserError):
            T.defer(self.st, card, "  ")
        self.assertEqual(len(self.events()), n)
        T.defer(self.st, card, "テスト環境が無い")
        self.assertEqual(card.status, "deferred")
        self.assertEqual([c.status for c in card.criteria], ["pass", "unverified"])
        loaded = T.load(self.st, card.id)
        self.assertEqual(loaded.status, "deferred")
        self.assertEqual([c.status for c in loaded.criteria], ["pass", "unverified"])
        self.assertEqual(len(loaded.log), 1)
        ts, _, text = loaded.log[-1].partition(" ")
        self.assertIsNotNone(S.parse_ts(ts))
        self.assertEqual(text, "defer: テスト環境が無い")
        evs = self.events()[n:]
        self.assertEqual([e["type"] for e in evs], ["task_update"])
        self.assertEqual((evs[0]["task"], evs[0]["status"], evs[0]["changed"]), (card.id, "deferred", ["defer"]))

    def test_cli_close_maps_reasons_to_japanese(self):
        from core.ctx import cli
        card = self.card()
        T.add_criterion(self.st, card, "単体テストが通る", "pytest -q")
        old = os.environ.get("KISEKI_DA_HOME")
        os.environ["KISEKI_DA_HOME"] = str(self.home)
        try:
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = cli.main(["task", "close", card.id, "--sid", "s-test"])
            self.assertEqual(rc, 1)
            self.assertEqual(out.getvalue(), "C1: 証拠がありません\n")
            self.assertEqual(err.getvalue(), "完了条件の証拠が不足しています\n")
            self.tool_call("Bash", "pytest -q")
            T.set_evidence(self.st, card, "C1", "last")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                rc = cli.main(["task", "close", card.id, "--sid", "s-test"])
            self.assertEqual((rc, out.getvalue()), (0, "OK\n"))
        finally:
            if old is None:
                os.environ.pop("KISEKI_DA_HOME", None)
            else:
                os.environ["KISEKI_DA_HOME"] = old

    def test_cli_argument_errors_are_one_japanese_line(self):
        """argparse errors and a missing subcommand: exit 1, nothing on stdout, one Japanese stderr line;
        --help is Japanese too (BUILD_BRIEF §2, INTERFACES §2)."""
        from core.ctx import cli
        cases = [
            (["task", "defer", "t2"], "--reason を指定してください"),
            (["task", "defer", "t2", "--reason"], "--reason に値がありません"),
            (["task", "set", "t", "--risk", "R9"], "--risk は 'R0', 'R1', 'R2', 'R3' のいずれかです（指定値: 'R9'）"),
            (["task", "set", "t", "--foo"], "不明な引数です: --foo"),
            (["build", "--budget", "abc"], "--budget は整数で指定してください（指定値: 'abc'）"),
            (["report"], "--week --audit のいずれかを指定してください"),
            (["report", "--week", "--audit"], "--audit と --week は同時に指定できません"),
            ([], "サブコマンドを指定してください（一覧: kiseki-da -h）"),
            (["task"], "サブコマンドを指定してください（一覧: kiseki-da task -h）"),
            (["candidate"], "サブコマンドを指定してください（一覧: kiseki-da candidate -h）"),
            (["evals"], "サブコマンドを指定してください（一覧: kiseki-da evals -h）"),
        ]
        with mock.patch.dict(os.environ, {"KISEKI_DA_HOME": str(self.home)}):
            for argv, expected in cases:
                out, err = io.StringIO(), io.StringIO()
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    rc = cli.main(argv)
                self.assertEqual((rc, out.getvalue()), (1, ""), argv)
                self.assertEqual(err.getvalue(), f"引数が不正です: {expected}\n", argv)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                rc = cli.main(["task", "--help"])
        self.assertEqual(rc, 0)
        text = out.getvalue()
        self.assertTrue(text.startswith("使い方: kiseki-da task "), text)
        self.assertIn("このヘルプを表示して終了する", text)
        for frag in ("usage:", "positional arguments", "options:", "show this help"):
            self.assertNotIn(frag, text)
        for sub in ("new", "show", "list", "set", "close", "defer", "brief"):
            self.assertIn(f"  {sub} ", text)

    def test_evals_run_argument_errors_are_one_japanese_line(self):
        """evals/run.py parses its own flags (cli.py only execs it, so cli.py's translation never sees them):
        an explicit value on a flag and an unknown flag are exit 1, nothing on stdout, one Japanese stderr
        line with the same wording as cli.py (BUILD_BRIEF §2, DECISIONS 2026-09-04 run.py)."""
        runner = S.REPO_ROOT / "evals" / "run.py"
        cases = [
            (["--dry-run=x"], "--dry-run は値を取りません（指定値: 'x'）"),
            (["--dry-run", "--json=1"], "--json は値を取りません（指定値: '1'）"),
            (["-h=x"], "-h/--help は値を取りません（指定値: 'x'）"),
            (["--bogus"], "不明な引数 --bogus"),
        ]
        for argv, expected in cases:
            r = subprocess.run([sys.executable, str(runner), *argv], capture_output=True, encoding="utf-8",
                               cwd=str(self.home), timeout=60)
            self.assertEqual((r.returncode, r.stdout), (1, ""), argv)
            self.assertEqual(r.stderr, f"引数が不正です: {expected}\n", argv)


# ---------------------------------------------------------------- brief

class BriefTests(TaskcardTestCase):
    HEADINGS = ["# 目標", "# 対象範囲", "# 禁止事項", "# 返却形式"]

    @staticmethod
    def headings(text: str) -> list[str]:
        return [line for line in text.splitlines() if line.startswith("#")]

    @staticmethod
    def section(text: str, start: str, end: str) -> str:
        return text.split(start, 1)[1].split(end, 1)[0]

    def test_research_brief(self):
        card = self.card()
        n = len(self.events())
        text = T.brief(self.st, card, "research", None)
        self.assertEqual(self.headings(text), self.HEADINGS)
        self.assertIn(card.goal, self.section(text, "# 目標", "# 対象範囲"))
        self.assertIn(card.goal, self.section(text, "# 対象範囲", "# 禁止事項"))
        forbid = self.section(text, "# 禁止事項", "# 返却形式")
        for word in ("Read", "Grep", "Glob", "WebFetch", "WebSearch", "ctx", "KISEKI_DA_HOME", "core/", "入れ子", "データ"):
            self.assertIn(word, forbid)
        ret = text.split("# 返却形式", 1)[1]
        for word in ("1.5K", "結論", "根拠（出典）", "未確認"):
            self.assertIn(word, ret)
        self.assertTrue(text.endswith("\n"))
        evs = self.events()[n:]
        self.assertEqual(len(evs), 1)
        self.assertEqual((evs[0]["type"], evs[0]["task"], evs[0]["role"], evs[0]["tokens_est"]),
                         ("worker_dispatch", card.id, "research", S.estimate_tokens(text)))
        self.assertGreater(evs[0]["tokens_est"], 0)
        text2 = T.brief(self.st, card, "research", " core/ctx/store.py の TOML emitter ")
        scope = self.section(text2, "# 対象範囲", "# 禁止事項")
        self.assertIn("core/ctx/store.py の TOML emitter", scope)
        self.assertNotIn(card.goal, scope)
        self.assertEqual(self.headings(text2), self.HEADINGS)

    def test_review_brief_lists_criteria(self):
        card = self.card()
        T.add_criterion(self.st, card, "単体テストが通る", "pytest -q")
        T.add_criterion(self.st, card, "差分を読み返した", "Read git diff")
        text = T.brief(self.st, card, "review", None)
        self.assertEqual(self.headings(text), self.HEADINGS)
        scope = self.section(text, "# 対象範囲", "# 禁止事項")
        for word in (card.goal, "C1", "単体テストが通る", "pytest -q", "C2", "差分を読み返した", "Read git diff"):
            self.assertIn(word, scope)
        self.assertIn("file:line", text.split("# 返却形式", 1)[1])
        ev = self.events({"worker_dispatch"})[-1]
        self.assertEqual((ev["task"], ev["role"], ev["tokens_est"]), (card.id, "review", S.estimate_tokens(text)))
        empty = self.card(goal="完了条件の無いカード")
        self.assertEqual(self.headings(T.brief(self.st, empty, "review", None)), self.HEADINGS)

    def test_brief_rejects_unknown_role(self):
        card = self.card()
        n = len(self.events())
        for role in ("builder", "", "Research"):
            with self.assertRaises(UserError):
                T.brief(self.st, card, role, None)
        self.assertEqual(len(self.events()), n)


if __name__ == "__main__":
    unittest.main()
