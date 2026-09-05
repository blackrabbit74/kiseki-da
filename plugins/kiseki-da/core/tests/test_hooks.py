"""Claude Code/Codex hook normalization, dispatch, candidate extraction, and fail-open tests."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from core.ctx import hooks, store as S, taskcard
from core.ctx.hooks import HookInput, HookOutput
from core.ctx.store import Store

FX = S.REPO_ROOT / "acceptance" / "fixtures"
if not FX.is_dir():
    FX = S.REPO_ROOT.parents[1] / "acceptance" / "fixtures"
CLI = S.REPO_ROOT / "core" / "ctx" / "cli.py"
TRANSCRIPT = FX / "transcript.jsonl"
SHA_EMPTY = hashlib.sha256(b"").hexdigest()[:12]


def fixture(name: str, cwd: str) -> dict:
    """__FX__ = fixtures dir, __CWD__ = the test workspace, __REPO__ = this checkout (codex-pre-tool-patch.json)."""
    text = (FX / name).read_text(encoding="utf-8").replace("__FX__", str(FX)).replace("__CWD__", cwd)
    text = text.replace("__REPO__", str(S.REPO_ROOT))
    return json.loads(text)


def make_hi(env: str, event: str, **kw) -> HookInput:
    base = dict(env=env, event=event, sid="s-x", cwd="", transcript_path=None, tool=None, tool_input=None,
                tool_ok=None, tool_output_text=None, source=None, stop_hook_active=False, raw={})
    base.update(kw)
    return HookInput(**base)


class HookBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = (Path(self.tmp.name) / "pa").resolve()
        self.ws = (Path(self.tmp.name) / "ws").resolve()
        (self.ws / "repo").mkdir(parents=True)
        patcher = mock.patch.dict(os.environ, {"KISEKI_DA_HOME": str(self.home)})
        patcher.start()
        self.addCleanup(patcher.stop)
        Store(home=self.home).init()

    def run_hook(self, event: str, payload: dict, env: str | None = "claude-code"):
        hi = hooks.parse_input(payload, env, event)
        st = Store(home=self.home, sid=hi.sid)
        out = hooks.handle(st, hi)
        stdout, stderr, code = hooks.format_output(hi, out)
        self.assertEqual(stderr, "")
        self.assertEqual(code, 0)
        return hi, out, stdout, st

    def run_fixture(self, event: str, name: str):
        return self.run_hook(event, fixture(name, str(self.ws)))

    def events(self, types: set[str] | None = None, sid: str | None = None) -> list[dict]:
        return list(Store(home=self.home).iter_events(types=types, sid=sid))


# ---------------------------------------------------------------- claude-code fixtures (smoke C1–C8)

class ClaudeCodeFixtureTestCase(HookBase):
    def test_concurrent_claude_codex_sessions_require_explicit_sid_and_keep_gate(self):
        base = {"cwd": str(self.ws / "repo"), "source": "startup"}
        self.run_hook("session-start", {**base, "session_id": "claude-A",
                                        "hook_event_name": "SessionStart"}, "claude-code")
        self.run_hook("session-start", {**base, "session_id": "codex-B",
                                        "hook_event_name": "SessionStart"}, "codex")
        anonymous = Store(home=self.home)
        self.assertEqual(set(anonymous.active_sids()), {"claude-A", "codex-B"})
        self.assertIsNone(anonymous.current_sid())
        env = os.environ.copy()
        denied = subprocess.run(
            [sys.executable, str(CLI), "task", "new", "--goal", "must not mix",
             "--risk", "R1", "--id", "sid-card"],
            cwd=self.ws / "repo", env=env, capture_output=True, text=True, check=False,
        )
        self.assertEqual(denied.returncode, 1)
        self.assertIn("複数session", denied.stderr)
        self.assertFalse((self.home / "tasks" / "sid-card.md").exists())

        explicit = subprocess.run(
            [sys.executable, str(CLI), "task", "new", "--goal", "belongs to A",
             "--risk", "R1", "--id", "sid-card", "--sid", "claude-A"],
            cwd=self.ws / "repo", env=env, capture_output=True, text=True, check=False,
        )
        self.assertEqual(explicit.returncode, 0, explicit.stderr)
        _, out, stdout, _ = self.run_hook(
            "stop", {"session_id": "claude-A", "cwd": str(self.ws / "repo"),
                     "hook_event_name": "Stop", "stop_hook_active": False}, "claude-code",
        )
        self.assertEqual(out.decision, "block")
        self.assertIn("--sid claude-A", stdout)

        for sid, host in (("claude-A", "claude-code"), ("codex-B", "codex")):
            self.run_hook("session-end", {"session_id": sid, "cwd": str(self.ws / "repo"),
                                          "hook_event_name": "SessionEnd", "reason": "test"}, host)
        self.assertEqual(anonymous.active_sids(), [])

    def test_c1_session_start_emits_context_and_events(self):
        hi, out, stdout, st = self.run_fixture("session-start", "cc-session-start.json")
        self.assertEqual((hi.env, hi.event, hi.sid, hi.source), ("claude-code", "session-start", "s-demo-1", "startup"))
        self.assertEqual(hi.cwd, str(self.ws / "repo"))
        self.assertEqual(hi.transcript_path, str(TRANSCRIPT))
        self.assertTrue(stdout)
        self.assertIn("session: s-demo-1", stdout)
        policy = (S.REPO_ROOT / "core" / "policy" / "interaction.md").read_text(encoding="utf-8").strip()
        self.assertEqual(stdout.count(policy), 1)
        self.assertEqual(stdout, out.context)
        self.assertEqual(Store(home=self.home).current_sid(), "s-demo-1")
        manifests = self.events({"context_manifest"}, sid="s-demo-1")
        self.assertEqual(len(manifests), 1)
        for key in ("budget", "used", "parts", "conflicts", "chars"):
            self.assertIn(key, manifests[0])
        self.assertLessEqual(manifests[0]["used"], 2500)
        starts = self.events({"session_start"}, sid="s-demo-1")
        self.assertEqual(len(starts), 1)
        self.assertEqual((starts[0]["env"], starts[0]["source"]), ("claude-code", "startup"))

    def test_c3a_post_tool_pytest(self):
        hi, out, stdout, st = self.run_fixture("post-tool", "cc-post-tool-pytest.json")
        self.assertEqual(stdout, "")
        self.assertIsNone(out.context)
        self.assertTrue(hi.tool_ok)
        self.assertEqual(hi.tool_output_text, "3 passed in 0.42s")
        evs = self.events({"tool_call"})
        self.assertEqual(len(evs), 1)
        ev = evs[0]
        self.assertEqual(ev["sid"], "s-demo-1")
        self.assertEqual(ev["tool"], "Bash")
        self.assertIs(ev["ok"], True)
        self.assertEqual(ev["target"], "pytest tests/test_auth.py -q")
        self.assertEqual(ev["out_len"], 17)
        self.assertEqual(ev["out_hash"], hashlib.sha256(b"3 passed in 0.42s").hexdigest()[:12])
        self.assertEqual(len(ev["out_hash"]), 12)

    def test_c3c_post_tool_read(self):
        hi, out, stdout, st = self.run_fixture("post-tool", "cc-post-tool-read.json")
        self.assertEqual(stdout, "")
        ev = self.events({"tool_call"})[0]
        self.assertEqual(ev["tool"], "Read")
        self.assertIs(ev["ok"], True)
        self.assertEqual(ev["target"], str(self.ws / "repo" / "git-diff.txt"))
        expected = S.dumps(hi.raw["tool_response"])
        self.assertEqual(ev["out_len"], len(expected))
        self.assertEqual(ev["out_hash"], hashlib.sha256(expected.encode("utf-8")).hexdigest()[:12])

    def test_c8f_post_tool_failure(self):
        hi, out, stdout, st = self.run_fixture("post-tool", "cc-post-tool-failure.json")
        self.assertEqual(stdout, "")
        self.assertIs(hi.tool_ok, False)
        self.assertIsNone(hi.tool_output_text)
        ev = self.events({"tool_call"})[0]
        self.assertIs(ev["ok"], False)
        self.assertEqual(ev["out_len"], 0)
        self.assertEqual(ev["out_hash"], "e3b0c44298fc")
        self.assertEqual(ev["target"], "pytest tests/test_other.py -q")

    def test_c4_stop_blocks_once_for_open_r1_card(self):
        st = Store(home=self.home, sid="s-demo-1")
        taskcard.new_card(st, "認証トークンの自動更新を追加する", risk="R1", id="demo-auth")
        hi, out, stdout, _ = self.run_fixture("stop", "cc-stop.json")
        self.assertFalse(hi.stop_hook_active)
        self.assertEqual(out.decision, "block")
        data = json.loads(stdout)
        self.assertEqual(data["decision"], "block")
        self.assertIn("demo-auth", data["reason"])
        self.assertIn("kiseki-da task close demo-auth", data["reason"])
        self.assertNotIn("additionalContext", stdout)
        hi, out, stdout, _ = self.run_fixture("stop", "cc-stop.json")
        self.assertEqual(stdout, "")
        self.assertIsNone(out.decision)
        gates = self.events({"gate"}, sid="s-demo-1")
        self.assertEqual([g["blocked"] for g in gates], [True, False])
        self.assertEqual([g["task"] for g in gates], ["demo-auth", None])

    def test_stop_without_cards_is_silent_but_logged(self):
        hi, out, stdout, _ = self.run_fixture("stop", "cc-stop.json")
        self.assertEqual(stdout, "")
        gates = self.events({"gate"})
        self.assertEqual(len(gates), 1)
        self.assertFalse(gates[0]["blocked"])

    def test_stop_hook_active_never_blocks(self):
        st = Store(home=self.home, sid="s-demo-1")
        taskcard.new_card(st, "x", risk="R1", id="demo-auth")
        payload = fixture("cc-stop.json", str(self.ws))
        payload["stop_hook_active"] = True
        hi, out, stdout, _ = self.run_hook("stop", payload)
        self.assertTrue(hi.stop_hook_active)
        self.assertEqual(stdout, "")
        gates = self.events({"gate"})
        self.assertEqual(len(gates), 1)
        self.assertEqual(gates[0]["reason"], "stop_hook_active")

    def test_c8a_pre_tool_rm_denied(self):
        hi, out, stdout, _ = self.run_fixture("pre-tool", "cc-pre-tool-rm.json")
        self.assertEqual(out.decision, "deny")
        data = json.loads(stdout)["hookSpecificOutput"]
        self.assertEqual(data["hookEventName"], "PreToolUse")
        self.assertEqual(data["permissionDecision"], "deny")
        self.assertTrue(data["permissionDecisionReason"])
        ev = self.events({"guard"})[0]
        self.assertEqual((ev["tool"], ev["decision"], ev["target"]), ("Bash", "deny", "rm -rf /"))
        self.assertEqual(ev["reason"], data["permissionDecisionReason"])

    def test_c8b_pre_tool_force_push_denied(self):
        hi, out, stdout, _ = self.run_fixture("pre-tool", "cc-pre-tool-push.json")
        self.assertEqual(json.loads(stdout)["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIn('"deny"', stdout)

    def test_c8c_pre_tool_deploy_asks(self):
        hi, out, stdout, _ = self.run_fixture("pre-tool", "cc-pre-tool-deploy.json")
        data = json.loads(stdout)["hookSpecificOutput"]
        self.assertEqual(data["permissionDecision"], "ask")
        self.assertIn("R3", data["permissionDecisionReason"])
        self.assertEqual(self.events({"guard"})[0]["decision"], "ask")

    def test_c8d_pre_tool_pytest_allow_is_empty(self):
        hi, out, stdout, _ = self.run_fixture("pre-tool", "cc-pre-tool-pytest.json")
        self.assertEqual(stdout, "")
        self.assertEqual(out.decision, "allow")
        ev = self.events({"guard"})[0]
        self.assertEqual((ev["decision"], ev["reason"], ev["target"]), ("allow", "", "pytest -q"))

    def test_c5_session_end_extracts_one_candidate(self):
        st = Store(home=self.home)
        st.set_current_sid("s-demo-1")
        hi, out, stdout, _ = self.run_fixture("session-end", "cc-session-end.json")
        self.assertEqual(stdout, "")
        pending = st.candidates("pending")
        self.assertEqual(len(pending), 1)
        self.assertIn("ISO 8601", pending[0]["text"])
        self.assertEqual(pending[0]["text"], "ありがとう。今後は日時のフォーマットは ISO 8601 で統一して")
        self.assertEqual(pending[0]["quote"], pending[0]["text"])
        self.assertEqual((pending[0]["kind"], pending[0]["source"]), ("preference", "user-stated"))
        ends = self.events({"session_end"}, sid="s-demo-1")
        self.assertEqual(len(ends), 1)
        self.assertEqual((ends[0]["reason"], ends[0]["candidates_created"]), ("other", 1))
        self.assertEqual(len(self.events({"candidate"})), 1)
        self.assertIsNone(st.current_sid())
        # a second session-end with the same transcript adds nothing new
        hi, out, stdout, _ = self.run_fixture("session-end", "cc-session-end.json")
        self.assertEqual(len(st.candidates("pending")), 1)
        self.assertEqual(self.events({"session_end"})[-1]["candidates_created"], 0)

    def test_session_end_keeps_current_sid_of_other_session(self):
        st = Store(home=self.home)
        st.set_current_sid("s-other")
        self.run_fixture("session-end", "cc-session-end.json")
        self.assertEqual(st.current_sid(), "s-other")

    def test_session_end_without_transcript(self):
        payload = fixture("cc-session-end.json", str(self.ws))
        del payload["transcript_path"]
        hi, out, stdout, _ = self.run_hook("session-end", payload)
        self.assertIsNone(hi.transcript_path)
        self.assertEqual(stdout, "")
        self.assertEqual(self.events({"session_end"})[0]["candidates_created"], 0)
        self.assertEqual(Store(home=self.home).candidates(), [])

    def test_session_end_with_missing_transcript_file(self):
        payload = fixture("cc-session-end.json", str(self.ws))
        payload["transcript_path"] = str(self.ws / "nope.jsonl")
        hi, out, stdout, _ = self.run_hook("session-end", payload)
        self.assertEqual(stdout, "")
        self.assertEqual(self.events({"session_end"})[0]["candidates_created"], 0)

    def test_every_hook_event_carries_the_payload_sid(self):
        st = Store(home=self.home, sid="s-demo-1")
        taskcard.new_card(st, "x", risk="R1", id="demo-auth")
        for event, name in (("post-tool", "cc-post-tool-pytest.json"), ("stop", "cc-stop.json"),
                            ("pre-tool", "cc-pre-tool-pytest.json"), ("session-end", "cc-session-end.json")):
            self.run_fixture(event, name)
        for ev in self.events():
            self.assertEqual(ev["sid"], "s-demo-1", ev)

    def test_target_is_redacted_and_capped(self):
        payload = fixture("cc-pre-tool-pytest.json", str(self.ws))
        payload["tool_input"]["command"] = "export API_KEY=abc123 && " + "x" * 300
        self.run_hook("pre-tool", payload)
        ev = self.events({"guard"})[0]
        self.assertTrue(ev["target"].startswith("export [REDACTED] && xxx"))
        self.assertNotIn("abc123", ev["target"])
        self.assertLessEqual(len(ev["target"]), 200)

    def test_post_tool_target_falls_back_to_dumps(self):
        payload = fixture("cc-post-tool-read.json", str(self.ws))
        payload["tool_name"] = "Grep"
        payload["tool_input"] = {"pattern": "token: hunter2", "path": "/x"}
        self.run_hook("post-tool", payload)
        ev = self.events({"tool_call"})[0]
        self.assertTrue(ev["target"].startswith('{"pattern": "[REDACTED]'))

    def test_claude_code_web_tools_get_no_context(self):
        payload = fixture("cc-post-tool-read.json", str(self.ws))
        payload["tool_name"] = "WebFetch"
        hi, out, stdout, _ = self.run_hook("post-tool", payload)
        self.assertIsNone(out.context)
        self.assertEqual(stdout, "")


class OtherEnvFixtureTestCase(HookBase):
    """Codex fixtures are derived from the official hook schema and run end to end."""

    def _run_all(self, prefix: str, env: str):
        names = sorted(p.name for p in FX.glob(f"{prefix}-*.json"))
        if not names:
            self.skipTest(f"no {prefix}-*.json fixtures yet (P3)")
        for name in names:
            with self.subTest(fixture=name):
                payload = fixture(name, str(self.ws))
                event = hooks.EVENT_NAMES[env].get(payload.get("hook_event_name", ""))
                self.assertIsNotNone(event, f"{name}: hook_event_name not normalizable")
                hi, out, stdout, _ = self.run_hook(event, payload, env)
                self.assertEqual(hi.env, env)
                if stdout:
                    json.loads(stdout)

    def test_codex_fixtures(self):
        self._run_all("codex", "codex")

    # ------------------------------------------------------------ codex
    def codex(self, name: str):
        payload = fixture(name, str(self.ws))
        return self.run_hook(hooks.EVENT_NAMES["codex"][payload["hook_event_name"]], payload, "codex")

    def test_codex_session_start(self):
        hi, out, stdout, st = self.codex("codex-session-start.json")
        self.assertEqual((hi.sid, hi.cwd, hi.source), ("cx-demo-1", str(self.ws / "repo"), "startup"))
        data = json.loads(stdout)["hookSpecificOutput"]
        self.assertEqual(data["hookEventName"], "SessionStart")
        self.assertIn("session: cx-demo-1", data["additionalContext"])
        self.assertEqual(data["additionalContext"], out.context)
        self.assertEqual(Store(home=self.home).current_sid(), "cx-demo-1")
        self.assertEqual(len(self.events({"context_manifest"}, sid="cx-demo-1")), 1)
        start = self.events({"session_start"}, sid="cx-demo-1")[0]
        self.assertEqual((start["env"], start["source"]), ("codex", "startup"))

    def test_codex_pre_tool_rm_denied(self):
        hi, out, stdout, _ = self.codex("codex-pre-tool-rm.json")
        self.assertEqual((hi.tool, hi.tool_input), ("Bash", {"command": "rm -rf /"}))
        data = json.loads(stdout)["hookSpecificOutput"]
        self.assertEqual((data["hookEventName"], data["permissionDecision"]), ("PreToolUse", "deny"))
        self.assertTrue(data["permissionDecisionReason"])
        self.assertEqual(self.events({"guard"})[0]["decision"], "deny")

    def test_codex_pre_tool_ask_is_sent_as_deny(self):
        hi, out, stdout, _ = self.codex("codex-pre-tool-deploy.json")
        self.assertEqual(out.decision, "ask")
        data = json.loads(stdout)["hookSpecificOutput"]
        self.assertEqual(data["permissionDecision"], "deny")
        self.assertEqual(data["permissionDecisionReason"], hooks.CODEX_ASK_REASON)
        self.assertEqual(self.events({"guard"})[0]["decision"], "ask")

    def test_codex_apply_patch_command_key_and_core_deny(self):
        hi, out, stdout, _ = self.codex("codex-pre-tool-patch.json")
        self.assertEqual(hi.tool, "Edit")
        self.assertEqual(hi.tool_input["file_paths"], ["core/ctx/store.py"])
        self.assertEqual(hi.cwd, str(S.REPO_ROOT))
        self.assertEqual(out.decision, "deny")
        self.assertIn("core/", out.reason)
        self.assertEqual(json.loads(stdout)["hookSpecificOutput"]["permissionDecision"], "deny")
        ev = self.events({"guard"})[0]
        self.assertEqual(ev["tool"], "Edit")
        self.assertTrue(ev["target"].startswith("*** Begin Patch"))

    def test_codex_pre_tool_allow_is_empty(self):
        hi, out, stdout, _ = self.codex("codex-pre-tool-pytest.json")
        self.assertEqual((out.decision, stdout), ("allow", ""))

    def test_codex_post_tool_string_response(self):
        hi, out, stdout, st = self.codex("codex-post-tool-pytest.json")
        self.assertEqual(stdout, "")
        self.assertIsNone(hi.tool_ok)
        ev = self.events({"tool_call"})[0]
        self.assertEqual((ev["tool"], ev["ok"], ev["target"], ev["out_len"]),
                         ("Bash", None, "pytest tests/test_auth.py -q", len("3 passed in 0.42s")))
        card = taskcard.new_card(st, "Codex string evidence must fail closed", id="codex-unknown")
        criterion = taskcard.add_criterion(st, card, "tests pass", "pytest -q")
        criterion.evidence = f"ev:{ev['sid']}:{ev['seq']}"
        self.assertEqual(taskcard.close(st, card), ["C1: result unknown"])

    def test_codex_post_tool_mcp_gets_external_context(self):
        hi, out, stdout, _ = self.codex("codex-post-tool-mcp.json")
        self.assertEqual(json.loads(stdout), {"hookSpecificOutput": {"hookEventName": "PostToolUse",
                                                                     "additionalContext": hooks.EXTERNAL_CONTEXT}})
        ev = self.events({"tool_call"})[0]
        self.assertEqual((ev["tool"], ev["ok"]), ("mcp__filesystem__read_file", True))

    def test_codex_stop_blocks_once(self):
        st = Store(home=self.home, sid="cx-demo-1")
        taskcard.new_card(st, "x", risk="R1", id="cx-card")
        hi, out, stdout, _ = self.codex("codex-stop.json")
        self.assertFalse(hi.stop_hook_active)
        data = json.loads(stdout)
        self.assertEqual(data["decision"], "block")
        self.assertIn("kiseki-da task close cx-card", data["reason"])
        self.assertEqual(set(data), {"decision", "reason"})
        hi, out, stdout, _ = self.codex("codex-stop.json")
        self.assertEqual(stdout, "")
        self.assertEqual([g["blocked"] for g in self.events({"gate"}, sid="cx-demo-1")], [True, False])

    def test_codex_stop_without_cards_is_silent(self):
        self.assertEqual(self.codex("codex-stop.json")[2], "")

    def test_codex_session_end_without_claude_code_transcript(self):
        Store(home=self.home).set_current_sid("cx-demo-1")
        hi, out, stdout, st = self.codex("codex-session-end.json")
        self.assertEqual(stdout, "")
        self.assertEqual(hi.transcript_path, str(self.ws / "rollout.jsonl"))
        end = self.events({"session_end"}, sid="cx-demo-1")[0]
        self.assertEqual((end["reason"], end["candidates_created"]), ("other", 0))
        self.assertEqual(Store(home=self.home).candidates(), [])
        self.assertIsNone(Store(home=self.home).current_sid())

# ---------------------------------------------------------------- parse_input normalization

class ParseInputTestCase(HookBase):
    def test_cursor_environment_is_explicitly_unsupported(self):
        self.assertNotIn("cursor", hooks.EVENT_NAMES)
        with self.assertRaisesRegex(ValueError, "unknown env"):
            hooks.parse_input({"hook_event_name": "sessionStart"}, "cursor", "session-start")

    def test_auto_detect_env(self):
        self.assertEqual(hooks.parse_input({"hook_event_name": "SessionStart"}, None, "session-start").env,
                         "claude-code")
        self.assertEqual(hooks.parse_input({}, None, "stop").env, "claude-code")
        self.assertEqual(hooks.parse_input({"hook_event_name": "SessionStart"}, "codex", "session-start").env, "codex")
        with self.assertRaises(ValueError):
            hooks.parse_input({"hook_event_name": "sessionStart"}, None, "session-start")

    def test_event_hint_is_trusted_when_name_absent(self):
        hi = hooks.parse_input({"session_id": "s"}, "claude-code", "pre-tool")
        self.assertEqual((hi.event, hi.sid, hi.cwd, hi.transcript_path, hi.tool, hi.tool_input),
                         ("pre-tool", "s", "", None, None, None))

    def test_mismatch_and_unknown_raise(self):
        pre = fixture("cc-pre-tool-pytest.json", str(self.ws))
        with self.assertRaises(ValueError):
            hooks.parse_input(pre, "claude-code", "stop")
        with self.assertRaises(ValueError):
            hooks.parse_input({"hook_event_name": "Bogus"}, "claude-code", "stop")
        with self.assertRaises(ValueError):
            hooks.parse_input({"hook_event_name": "PostToolUseFailure"}, "codex", "post-tool")   # Codex has none
        with self.assertRaises(ValueError):
            hooks.parse_input({"hook_event_name": "sessionStart"}, "cursor", "session-start")
        with self.assertRaises(ValueError):
            hooks.parse_input(pre, "claude-code", "bogus-event")
        with self.assertRaises(ValueError):
            hooks.parse_input(pre, "emacs", "pre-tool")
        with self.assertRaises(ValueError):
            hooks.parse_input([], "claude-code", "pre-tool")  # type: ignore[arg-type]

    def test_all_names_normalize(self):
        for env, table in hooks.EVENT_NAMES.items():
            for raw, event in table.items():
                hi = hooks.parse_input({"hook_event_name": raw}, env, event)
                self.assertEqual((hi.env, hi.event), (env, event))
                self.assertEqual(hi.raw["hook_event_name"], raw)
        self.assertEqual(set(hooks.EVENT_NAMES["claude-code"].values()), set(hooks.EVENTS))

    def test_missing_values_default(self):
        hi = hooks.parse_input({"session_id": "", "cwd": None, "transcript_path": ""}, "claude-code", "stop")
        self.assertEqual((hi.sid, hi.cwd, hi.transcript_path, hi.stop_hook_active), ("nosession", "", None, False))

    def test_claude_code_tool_ok_rules(self):
        base = {"session_id": "s", "hook_event_name": "PostToolUse", "tool_name": "Bash",
                "tool_input": {"command": "x"}}
        cases = [
            ({"tool_response": {"stdout": "out", "stderr": "", "interrupted": False}}, True, "out"),
            ({"tool_response": {"stdout": "out", "interrupted": True}}, False, "out"),
            ({"tool_response": {"stdout": "", "error": "nope"}}, False, ""),
            ({"tool_response": {"is_error": True}}, False, ""),
            ({"tool_response": {"isError": True, "stdout": "x"}}, False, "x"),
            ({"tool_response": "plain text"}, True, "plain text"),
            ({}, None, None),
        ]
        for extra, ok, text in cases:
            hi = hooks.parse_input({**base, **extra}, "claude-code", "post-tool")
            self.assertIs(hi.tool_ok, ok, extra)
            self.assertEqual(hi.tool_output_text, text, extra)
        hi = hooks.parse_input({**base, "hook_event_name": "PostToolUseFailure",
                                "tool_response": {"stdout": "x"}}, "claude-code", "post-tool")
        self.assertIs(hi.tool_ok, False)
        self.assertEqual(hi.tool_output_text, "x")
        hi = hooks.parse_input({**base, "tool_name": "Read", "tool_response": {"a": 1}}, "claude-code", "post-tool")
        self.assertEqual(hi.tool_output_text, '{"a": 1}')

    def test_codex_apply_patch_becomes_edit_with_file_paths(self):
        patch = ("*** Begin Patch\n*** Update File: core/ctx/store.py\n@@\n-a\n+b\n"
                 "*** Add File: docs/new.md\n+hello\n*** Delete File: old.txt\n"
                 "*** Update File: a.py\n*** Move to: b.py\n*** End Patch\n")
        payload = {"session_id": "cx", "hook_event_name": "PreToolUse", "tool_name": "apply_patch",
                   "tool_input": {"patch": patch}, "cwd": str(S.REPO_ROOT)}
        hi = hooks.parse_input(payload, "codex", "pre-tool")
        self.assertEqual(hi.tool, "Edit")
        self.assertEqual(hi.tool_input["file_paths"], ["core/ctx/store.py", "docs/new.md", "old.txt", "a.py", "b.py"])
        self.assertEqual(hi.tool_input["patch"], patch)
        out = hooks.handle(Store(home=self.home, sid=hi.sid), hi)
        self.assertEqual(out.decision, "deny")
        self.assertIn("core/", out.reason)
        stdout, _, _ = hooks.format_output(hi, out)
        self.assertEqual(json.loads(stdout)["hookSpecificOutput"]["permissionDecision"], "deny")
        # patch text under another key, and a safe path
        payload["tool_input"] = {"input": "*** Add File: README2.md\n+x\n"}
        hi = hooks.parse_input(payload, "codex", "pre-tool")
        self.assertEqual(hi.tool_input["file_paths"], ["README2.md"])
        self.assertEqual(hooks.handle(Store(home=self.home, sid=hi.sid), hi).decision, "allow")
        payload["tool_input"] = {"text": "*** Delete File: x"}
        self.assertEqual(hooks.parse_input(payload, "codex", "pre-tool").tool_input["file_paths"], ["x"])
        payload["tool_input"] = {"nothing": 1}
        self.assertEqual(hooks.parse_input(payload, "codex", "pre-tool").tool_input["file_paths"], [])

    def test_codex_bash_passes_through(self):
        hi = hooks.parse_input({"session_id": "cx", "hook_event_name": "PreToolUse", "tool_name": "Bash",
                                "tool_input": {"command": "ls"}}, "codex", "pre-tool")
        self.assertEqual((hi.tool, hi.tool_input), ("Bash", {"command": "ls"}))


# ---------------------------------------------------------------- handle / format_output per environment

class FormatOutputTestCase(HookBase):
    def test_session_start_shapes(self):
        out = HookOutput(context="常駐\nsession: s-x")
        self.assertEqual(hooks.format_output(make_hi("claude-code", "session-start"), out), ("常駐\nsession: s-x", "", 0))
        stdout, _, _ = hooks.format_output(make_hi("codex", "session-start"), out)
        self.assertEqual(json.loads(stdout), {"hookSpecificOutput": {"hookEventName": "SessionStart",
                                                                     "additionalContext": out.context}})
        self.assertEqual(hooks.format_output(make_hi("claude-code", "session-start"), HookOutput())[0], "")

    def test_post_tool_context_shapes(self):
        out = HookOutput(context=hooks.EXTERNAL_CONTEXT)
        hi = make_hi("codex", "post-tool", raw={"hook_event_name": "PostToolUse"})
        self.assertEqual(json.loads(hooks.format_output(hi, out)[0]),
                         {"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": hooks.EXTERNAL_CONTEXT}})
        hi = make_hi("claude-code", "post-tool", raw={"hook_event_name": "PostToolUseFailure"})
        self.assertEqual(json.loads(hooks.format_output(hi, out)[0])["hookSpecificOutput"]["hookEventName"],
                         "PostToolUseFailure")
        hi = make_hi("claude-code", "post-tool", raw={})
        self.assertEqual(json.loads(hooks.format_output(hi, out)[0])["hookSpecificOutput"]["hookEventName"], "PostToolUse")
    def test_external_context_only_outside_claude_code(self):
        for env, tool, expect in (("codex", "WebFetch", True),
                                  ("codex", "mcp__github__search", True),
                                  ("codex", "Bash", False),
                                  ("claude-code", "WebFetch", False)):
            hi = make_hi(env, "post-tool", sid=f"s-{env}", tool=tool, tool_input={"url": "https://x"},
                         tool_ok=True, tool_output_text="body")
            out = hooks.handle(Store(home=self.home, sid=hi.sid), hi)
            self.assertEqual(out.context == hooks.EXTERNAL_CONTEXT, expect, (env, tool))
            self.assertIsNone(out.decision)

    def test_pre_tool_shapes(self):
        deny = HookOutput(decision="deny", reason="だめ")
        ask = HookOutput(decision="ask", reason="R3")
        cc = json.loads(hooks.format_output(make_hi("claude-code", "pre-tool", raw={"hook_event_name": "PreToolUse"}), deny)[0])
        self.assertEqual(cc, {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                                    "permissionDecisionReason": "だめ"}})
        cc = json.loads(hooks.format_output(make_hi("claude-code", "pre-tool"), ask)[0])
        self.assertEqual(cc["hookSpecificOutput"]["permissionDecision"], "ask")
        self.assertEqual(cc["hookSpecificOutput"]["permissionDecisionReason"], "R3")
        # codex: deny as is, ask → deny with the fixed reason
        cx = json.loads(hooks.format_output(make_hi("codex", "pre-tool"), deny)[0])
        self.assertEqual(cx["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertEqual(cx["hookSpecificOutput"]["permissionDecisionReason"], "だめ")
        cx = json.loads(hooks.format_output(make_hi("codex", "pre-tool"), ask)[0])
        self.assertEqual(cx["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertEqual(cx["hookSpecificOutput"]["permissionDecisionReason"], hooks.CODEX_ASK_REASON)
        self.assertIn("task override", hooks.CODEX_ASK_REASON)
    def test_allow_is_always_empty_and_never_says_allow(self):
        allow = HookOutput(decision="allow", reason="")
        for env in ("claude-code", "codex"):
            self.assertEqual(hooks.format_output(make_hi(env, "pre-tool"), allow), ("", "", 0))
            self.assertEqual(hooks.format_output(make_hi(env, "pre-tool"), HookOutput()), ("", "", 0))

    def test_codex_ask_keeps_ask_in_guard_event(self):
        hi = hooks.parse_input({"session_id": "cx", "hook_event_name": "PreToolUse", "tool_name": "Bash",
                                "tool_input": {"command": "vercel deploy --prod"}}, "codex", "pre-tool")
        out = hooks.handle(Store(home=self.home, sid="cx"), hi)
        self.assertEqual(out.decision, "ask")
        stdout, _, _ = hooks.format_output(hi, out)
        self.assertEqual(json.loads(stdout)["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertEqual(json.loads(stdout)["hookSpecificOutput"]["permissionDecisionReason"], hooks.CODEX_ASK_REASON)
        self.assertEqual(self.events({"guard"})[0]["decision"], "ask")

    def test_stop_shapes(self):
        block = HookOutput(decision="block", reason="閉じて")
        self.assertEqual(json.loads(hooks.format_output(make_hi("claude-code", "stop"), block)[0]),
                         {"decision": "block", "reason": "閉じて"})
        self.assertEqual(json.loads(hooks.format_output(make_hi("codex", "stop"), block)[0]),
                         {"decision": "block", "reason": "閉じて"})
        for env in ("claude-code", "codex"):
            self.assertEqual(hooks.format_output(make_hi(env, "stop"), HookOutput()), ("", "", 0))

    def test_session_end_for_codex_needs_claude_code_format(self):
        other = self.ws / "codex.jsonl"
        other.write_text('{"role": "user", "content": "今後は必ず ISO 8601"}\n', encoding="utf-8")
        hi = hooks.parse_input({"session_id": "cx", "hook_event_name": "SessionEnd", "transcript_path": str(other)},
                               "codex", "session-end")
        hooks.handle(Store(home=self.home, sid="cx"), hi)
        self.assertEqual(self.events({"session_end"})[0]["candidates_created"], 0)
        hi = hooks.parse_input({"session_id": "cx", "hook_event_name": "SessionEnd",
                                "transcript_path": str(TRANSCRIPT)}, "codex", "session-end")
        hooks.handle(Store(home=self.home, sid="cx"), hi)
        self.assertEqual(self.events({"session_end"})[1]["candidates_created"], 0)

    def test_unknown_event_in_handle_raises(self):
        with self.assertRaises(ValueError):
            hooks.handle(Store(home=self.home, sid="s"), make_hi("claude-code", "bogus"))


# ---------------------------------------------------------------- extract_candidates (pure)

class ExtractCandidatesTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def write(self, rows: list, name: str = "t.jsonl") -> Path:
        p = self.dir / name
        p.write_text("".join((r if isinstance(r, str) else json.dumps(r, ensure_ascii=False)) + "\n" for r in rows),
                     encoding="utf-8")
        return p

    @staticmethod
    def user(content, **extra) -> dict:
        return {"type": "user", "message": {"role": "user", "content": content}, **extra}

    def test_acceptance_transcript_yields_exactly_one(self):
        cands = hooks.extract_candidates(TRANSCRIPT)
        self.assertEqual(len(cands), 1)
        self.assertEqual(cands[0], {"text": "ありがとう。今後は日時のフォーマットは ISO 8601 で統一して",
                                    "quote": "ありがとう。今後は日時のフォーマットは ISO 8601 で統一して",
                                    "source": "user-stated", "kind": "preference"})
        self.assertTrue(hooks.is_claude_code_transcript(TRANSCRIPT))

    def test_exclusions(self):
        p = self.write([
            self.user("覚えて: A", isMeta=True),
            self.user([{"type": "tool_result", "tool_use_id": "t", "content": "常に"}]),
            self.user("<system-reminder>常に</system-reminder>"),
            self.user("<command-name>常に</command-name>"),
            self.user("<local-command-stdout>常に</local-command-stdout>"),
            self.user("常に" + "x" * 2001),
            {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "常に B"}]}},
            {"type": "user", "message": "not a dict 常に"},
            {"type": "user"},
            "not json 常に",
            self.user("今日は晴れ"),
            self.user([{"type": "tool_result", "content": "x"}, {"type": "text", "text": "覚えて: mixed"}]),
            self.user("必ず C\n二度と D\nplain\nnever do E\nAlways F\nRemember G"),
            self.user("必ず C"),
        ])
        cands = hooks.extract_candidates(p)
        self.assertEqual([c["text"] for c in cands],
                         ["覚えて: mixed", "必ず C", "二度と D", "never do E", "Always F", "Remember G"])
        kinds = {c["text"]: c["kind"] for c in cands}
        self.assertEqual(kinds["二度と D"], "constraint")
        self.assertEqual(kinds["never do E"], "constraint")
        self.assertEqual(kinds["必ず C"], "preference")
        self.assertEqual(kinds["Always F"], "preference")
        for c in cands:
            self.assertEqual(c["source"], "user-stated")
            self.assertEqual(c["quote"], c["text"])

    def test_constraint_words(self):
        p = self.write([self.user("今後は X を禁止\n今後は Y しない\nNEVER Z\n今後は W で")])
        self.assertEqual([c["kind"] for c in hooks.extract_candidates(p)],
                         ["constraint", "constraint", "constraint", "preference"])

    def test_exact_2000_chars_is_kept(self):
        p = self.write([self.user("常に" + "x" * 1998)])
        self.assertEqual(len(hooks.extract_candidates(p)), 1)

    def test_unreadable_returns_empty(self):
        self.assertEqual(hooks.extract_candidates(self.dir / "missing.jsonl"), [])
        self.assertEqual(hooks.extract_candidates(self.dir), [])
        self.assertFalse(hooks.is_claude_code_transcript(self.dir / "missing.jsonl"))

    def test_format_check(self):
        self.assertFalse(hooks.is_claude_code_transcript(self.write(["plain text", "{}"])))
        self.assertFalse(hooks.is_claude_code_transcript(self.write(["", '{"type": "user"}'])))
        self.assertFalse(hooks.is_claude_code_transcript(self.write(['[1, 2]'])))
        self.assertFalse(hooks.is_claude_code_transcript(self.write([])))
        self.assertTrue(hooks.is_claude_code_transcript(self.write(["", "  ", '{"type": "x", "message": null}'])))

    def test_tail_only_and_partial_first_line_dropped(self):
        rows = [self.user(f"常に {i:04d} " + "p" * 100) for i in range(50)]
        p = self.write(rows)
        full = hooks.extract_candidates(p)
        self.assertEqual(len(full), 50)
        tail = hooks.extract_candidates(p, max_bytes=1000)
        self.assertTrue(0 < len(tail) < 50)
        self.assertEqual([c["text"] for c in tail], [c["text"] for c in full[-len(tail):]])
        # exactly the file size: nothing is cut
        self.assertEqual(len(hooks.extract_candidates(p, max_bytes=p.stat().st_size)), 50)


# ---------------------------------------------------------------- fail-open through the real CLI

class SubprocessFailOpenTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = (Path(self.tmp.name) / "pa").resolve()
        self.ws = (Path(self.tmp.name) / "ws").resolve()
        self.ws.mkdir()
        Store(home=self.home).init()

    def run_cli(self, argv: list[str], stdin: str, **env: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(CLI), *argv], input=stdin, capture_output=True, encoding="utf-8",
                              env={**os.environ, "KISEKI_DA_HOME": str(self.home), **env}, cwd=str(self.ws), timeout=60)

    def raw_fixture(self, name: str) -> str:
        return (FX / name).read_text(encoding="utf-8").replace("__FX__", str(FX)).replace("__CWD__", str(self.ws))

    def errors(self) -> list[dict]:
        return list(Store(home=self.home).iter_events(types={"error"}))

    def assert_fail_open(self, argv: list[str], stdin: str, where: str):
        r = self.run_cli(argv, stdin)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, "")
        errs = self.errors()
        self.assertEqual(len(errs), 1, errs)
        self.assertEqual(errs[0]["where"], where)
        self.assertTrue(errs[0]["message"])

    def test_broken_json(self):
        r = self.run_cli(["hook", "pre-tool", "--env", "claude-code"], self.raw_fixture("cc-pre-tool-broken.json"))
        self.assertEqual((r.returncode, r.stdout), (0, ""))
        self.assertEqual(self.errors(), [])

    def test_broken_json_outside_project_scope_is_complete_noop(self):
        from core.ctx import scope
        project = self.ws / "registered"
        project.mkdir()
        scope.add_project(self.home, project)
        before = sorted((p.relative_to(self.home).as_posix(), p.read_bytes() if p.is_file() else None)
                        for p in self.home.rglob("*"))
        r = self.run_cli(["hook", "pre-tool", "--env", "claude-code"], '{"cwd": "broken"')
        after = sorted((p.relative_to(self.home).as_posix(), p.read_bytes() if p.is_file() else None)
                       for p in self.home.rglob("*"))
        self.assertEqual((r.returncode, r.stdout, after), (0, "", before))

    def test_unknown_event_name(self):
        self.assert_fail_open(["hook", "bogus", "--env", "claude-code"], self.raw_fixture("cc-pre-tool-pytest.json"),
                              "hook:bogus")

    def test_unknown_env(self):
        self.assert_fail_open(["hook", "pre-tool", "--env", "emacs"], self.raw_fixture("cc-pre-tool-pytest.json"),
                              "hook:pre-tool")

    def test_positional_payload_mismatch(self):
        self.assert_fail_open(["hook", "stop", "--env", "claude-code"], self.raw_fixture("cc-pre-tool-pytest.json"),
                              "hook:stop")

    def test_empty_stdin(self):
        r = self.run_cli(["hook", "pre-tool", "--env", "claude-code"], "")
        self.assertEqual((r.returncode, r.stdout), (0, ""))

    def test_allow_is_empty_stdout_exit_0(self):
        r = self.run_cli(["hook", "pre-tool", "--env", "claude-code"], self.raw_fixture("cc-pre-tool-pytest.json"))
        self.assertEqual((r.returncode, r.stdout, r.stderr), (0, "", ""))
        self.assertEqual(self.errors(), [])
        guards = list(Store(home=self.home).iter_events(types={"guard"}))
        self.assertEqual(len(guards), 1)
        self.assertEqual(guards[0]["decision"], "allow")

    def test_deny_and_ask_through_cli(self):
        r = self.run_cli(["hook", "pre-tool", "--env", "claude-code"], self.raw_fixture("cc-pre-tool-rm.json"))
        self.assertEqual(r.returncode, 0)
        self.assertEqual(json.loads(r.stdout)["hookSpecificOutput"]["permissionDecision"], "deny")
        r = self.run_cli(["hook", "pre-tool", "--env", "claude-code"], self.raw_fixture("cc-pre-tool-deploy.json"))
        self.assertEqual(json.loads(r.stdout)["hookSpecificOutput"]["permissionDecision"], "ask")
        r = self.run_cli(["hook", "post-tool", "--env", "claude-code"], self.raw_fixture("cc-post-tool-failure.json"))
        self.assertEqual((r.returncode, r.stdout), (0, ""))
        self.assertEqual(self.errors(), [])

    def test_deny_survives_non_utf8_stdio_codec(self):
        """The Japanese deny reason must reach stdout even when the locale codec cannot encode it; otherwise the
        hook fails open and the environment reads the empty stdout as allow (INTERFACES §6.3)."""
        payload = json.loads(self.raw_fixture("cc-pre-tool-rm.json"))
        payload["tool_input"]["command"] = "rm -rf / ; echo 完了"
        stdin = json.dumps(payload, ensure_ascii=False)
        envs = [{"PYTHONIOENCODING": "ascii"},
                {"LC_ALL": "en_US.ISO8859-1", "LC_CTYPE": "en_US.ISO8859-1", "LANG": "en_US.ISO8859-1",
                 "PYTHONUTF8": "0"}]
        for env in envs:
            r = self.run_cli(["hook", "pre-tool", "--env", "claude-code"], stdin, **env)
            self.assertEqual(r.returncode, 0, env)
            out = json.loads(r.stdout)["hookSpecificOutput"]
            self.assertEqual(out["permissionDecision"], "deny", env)
            self.assertIn("禁止", out["permissionDecisionReason"], env)
        self.assertEqual(self.errors(), [])
        guards = list(Store(home=self.home).iter_events(types={"guard"}))
        self.assertEqual([(g["decision"], g["target"]) for g in guards], [("deny", "rm -rf / ; echo 完了")] * 2)
        r = self.run_cli(["task", "defer", "t2"], "", PYTHONIOENCODING="ascii")  # the plain CLI shares the fix
        self.assertEqual((r.returncode, r.stdout, r.stderr), (1, "", "引数が不正です: --reason を指定してください\n"))


if __name__ == "__main__":
    unittest.main()
