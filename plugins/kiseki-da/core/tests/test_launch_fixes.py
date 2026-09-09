"""Launch regressions: actual hook/CLI paths, scope, user intent, evidence and recovery."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from core.ctx import build, evidence as E, gate, hooks, report, store, taskcard
from core.ctx import evidence as authority


class LaunchFixes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.ws = self.root / "project-a"
        self.ws.mkdir()
        self.st = store.Store(home=self.root / "state", sid="launch-a")
        self.st.init()
        self.st.set_workspace(str(self.ws))
        self.st.set_environment("codex")
        self.env = {**os.environ, "KISEKI_DA_HOME": str(self.st.home), "PYTHONDONTWRITEBYTECODE": "1"}
        self.patch = patch.dict(os.environ, {"KISEKI_DA_HOME": str(self.st.home)})
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def hook(self, event, raw_name, *, env="codex", **payload):
        raw = {"session_id": self.st.sid, "hook_event_name": raw_name, "cwd": str(self.ws), **payload}
        hi = hooks.parse_input(raw, env, event)
        return hooks.handle(self.st, hi), hi

    def user(self, text):
        self.hook("user-input", "UserPromptSubmit", prompt=text)

    def cli(self, *args, env=None, cwd=None):
        return subprocess.run([sys.executable, str(store.REPO_ROOT / "core/ctx/cli.py"),
                               "--home", str(self.st.home), "--sid", self.st.sid, *args],
                              cwd=cwd or self.ws, env=env or self.env, text=True, capture_output=True)

    def tool(self, tool="Bash", data=None, ok=True):
        data = data or {"command": "pytest tests/auth.py"}
        payload = {"tool_name": tool, "tool_input": data, "tool_use_id": f"call-{len(list(self.st.iter_events()))}",
                   "tool_response": {"exit_code": 0 if ok else 1, "stdout": "output"}}
        if tool != "Bash":
            payload["tool_response"] = {"success": ok, "isError": not ok}
        self.hook("post-tool", "PostToolUse", **payload)
        ev = self.st.last_event(types={"tool_call"})
        return f"ev:{ev['sid']}:{ev['seq']}"

    def card(self, check="pytest tests/auth.py"):
        c = taskcard.new_card(self.st, "Verify authentication", id="auth")
        taskcard.add_criterion(self.st, c, "Authentication works", check)
        return c

    def test_wrong_arguments_never_close(self):
        card = self.card()
        ref = self.tool(data={"command": "pytest tests/unrelated.py"})
        taskcard.set_evidence(self.st, card, "C1", ref)
        self.assertIn("request mismatch", " ".join(taskcard.close(self.st, card)))
        self.assertEqual(card.status, "open")

    def test_successful_bound_evidence_closes(self):
        card = self.card()
        taskcard.set_evidence(self.st, card, "C1", self.tool())
        self.assertEqual(taskcard.close(self.st, card), [])

    def test_failed_read_and_unknown_shell_are_rejected(self):
        for tool, ok, check in [("Read", False, "Read config.toml"), ("Bash", None, "pytest tests/auth.py")]:
            data = {"file_path": "config.toml"} if tool == "Read" else {"command": check}
            ref = self.st.append_event({"type": "tool_call", "tool": tool, "ok": ok, "tool_use_id": "call-1",
                                        "cwd": str(self.ws), "request_hash": E.identity(tool, data, str(self.ws))})
            self.assertIsNotNone(taskcard.check_evidence(self.st, taskcard.Criterion("C1", "check", check, ref)))

    def test_codex_exit_status_is_not_inferred_from_positive_words(self):
        for output, expected in [("3 passed", None), ("Process exited with code 1\nFAILED", None),
                                 ("Process exited with code 0\nOK", None)]:
            _, hi = self.hook("post-tool", "PostToolUse", tool_name="Bash", tool_input={"command": "pytest"},
                              tool_use_id="call", tool_response=output)
            self.assertIs(hi.tool_ok, expected)

    def test_later_edit_invalidates_test_result(self):
        card = self.card()
        taskcard.set_evidence(self.st, card, "C1", self.tool())
        self.tool("Edit", {"file_path": str(self.ws / "auth.py")})
        self.assertIn("evidence stale", " ".join(taskcard.close(self.st, card)))

    def test_two_registered_project_checkers_do_not_invalidate_each_other(self):
        card = self.card("python3 validate_doc.py output.docx")
        taskcard.add_criterion(self.st, card, "Layout is checked", "python3 check_layout.py output.docx")
        taskcard.set_evidence(self.st, card, "C1", self.tool(data={"command": card.criteria[0].check}))
        taskcard.set_evidence(self.st, card, "C2", self.tool(data={"command": card.criteria[1].check}))
        self.assertEqual(taskcard.missing_evidence(self.st, card), [])
        self.tool(data={"command": "python3 rewrite_doc.py output.docx"})
        self.assertEqual(len(taskcard.missing_evidence(self.st, card)), 2)

    def test_read_snapshot_detects_external_file_change(self):
        target = self.ws / "config.toml"
        target.write_text("value=1")
        card = self.card("Read config.toml")
        taskcard.set_evidence(self.st, card, "C1", self.tool("Read", {"file_path": str(target)}))
        target.write_text("value=2")
        self.assertIn("artifact changed", " ".join(taskcard.close(self.st, card)))

    def test_cross_project_evidence_is_rejected(self):
        card = self.card()
        ref = self.tool()
        card.workspace = str(self.root / "project-b")
        taskcard.set_evidence(self.st, card, "C1", ref)
        self.assertIn("workspace mismatch", " ".join(taskcard.close(self.st, card)))

    def test_last_never_falls_back_to_another_session(self):
        self.tool()
        foreign = store.Store(home=self.st.home, sid="other")
        with self.assertRaises(store.UserError):
            taskcard._resolve_evidence_ref(foreign, "last")

    def test_risk_and_defer_cannot_be_used_to_fake_completion(self):
        card = self.card()
        taskcard.set_risk(self.st, card, "R3")
        with self.assertRaises(store.UserError):
            taskcard.set_risk(self.st, card, "R0")
        with self.assertRaises(store.UserError):
            taskcard.set_status(self.st, card, "deferred")

    def test_constraints_and_next_step_are_available_through_cli(self):
        card = self.card()
        result = self.cli("task", "set", card.id, "--constraint", "Do not change billing", "--next", "Review the diff")
        self.assertEqual(result.returncode, 0, result.stderr)
        loaded = taskcard.load(self.st, card.id)
        self.assertEqual(loaded.constraints, ["Do not change billing"])
        self.assertEqual(loaded.next_action, "Review the diff")
        self.assertIn("Do not change billing", taskcard.brief(self.st, loaded, "review", None))

    def test_long_card_keeps_identity_and_reference(self):
        card = self.card()
        card.goal = "長い目標。" * 1500
        taskcard.set_next(self.st, card, "次に検証する")
        text, manifest = build.build(self.st)
        self.assertIn(card.id, text)
        self.assertIn("kiseki-da task show auth", text)
        self.assertIn("省略", text)
        self.assertLessEqual(manifest["used"], 2500)
        self.assertLessEqual(len(text), 9000)

    def test_eleven_short_constraints_are_not_silently_cut(self):
        p = self.st.read_profile()
        p["constraints"] = [{"id": f"c{i}", "text": f"必須条件{i}"} for i in range(11)]
        self.st.write_profile(p)
        text, _ = build.build(self.st)
        self.assertIn("必須条件10", text)

    def test_all_required_pages_must_be_read_before_edits(self):
        p = self.st.read_profile()
        p["constraints"] = [{"id": "c1", "text": "重要な制約。" * 1300}]
        self.st.write_profile(p)
        text, manifest = build.build(self.st)
        self.st.append_event({"type": "context_manifest", **manifest})
        self.assertIn("kiseki-da context required", text)
        self.assertTrue(build.needs_context(self.st))
        def attempt():
            return self.hook("pre-tool", "PreToolUse", tool_name="apply_patch",
                             tool_input={"command": "*** Begin Patch\n*** Add File: x.txt\n+x\n*** End Patch"})[0]
        self.assertEqual(attempt().decision, "deny")
        pages = build.required_context(self.st)["pages"]
        for n in range(1, len(pages) + 1):
            result = self.cli("context", "required", "--page", str(n))
            self.assertEqual(result.returncode, 0, result.stderr)
            if n < len(pages):
                self.assertTrue(build.needs_context(self.st))
        self.assertFalse(build.needs_context(self.st))
        self.assertEqual(attempt().decision, "allow")
        p["constraints"][0]["text"] += "追加条件"
        self.st.write_profile(p)
        self.assertTrue(build.needs_context(self.st))

    def test_too_small_budget_reports_failure_without_losing_required_info(self):
        with self.assertRaises(store.UserError):
            build.build(self.st, budget=10)

    def test_policy_can_be_loaded_from_an_unrelated_folder(self):
        result = self.cli("policy", "show", "decision-support")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("意思決定", result.stdout)

    def test_fixed_entry_binds_the_selected_home(self):
        command = E.simple_words(build.command_prefix(self.st.home))
        env = dict(self.env, KISEKI_DA_HOME=str(self.root / "wrong-home"))
        payload = {"session_id": "generated", "hook_event_name": "SessionStart", "cwd": str(self.ws)}
        result = subprocess.run([*command, "hook", "session-start", "--env", "codex"],
                                input=json.dumps(payload), text=True, env=env, cwd=self.ws, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout)
        self.assertFalse((self.root / "wrong-home").exists())

    def test_verify_runner_binds_real_execution_to_the_exact_criterion(self):
        command = [sys.executable, "-c", "print('verified')"]
        card = taskcard.new_card(self.st, "検証runnerの証拠", id="runner-proof")
        taskcard.add_criterion(self.st, card, "実行が成功する", shlex.join(command))
        if os.name == "nt":
            taskcard.add_criterion(self.st, card, "Windows表記も同じ実行を指す", subprocess.list2cmdline(command))
        result = self.cli("verify", "run", "--", *command)
        self.assertEqual(result.returncode, 0, result.stderr)
        taskcard.set_evidence(self.st, card, "C1", "last")
        if os.name == "nt":
            taskcard.set_evidence(self.st, card, "C2", "last")
        self.assertEqual(taskcard.close(self.st, card), [])
        event = list(self.st.iter_events(types={"tool_call"}))[-1]
        self.assertTrue(event["tool_use_id"].startswith("verify-"))
        self.assertEqual(event["workspace"], str(self.ws))
        ordinary = {**event, "tool_use_id": "ordinary-call", "request_hash": "different"}
        self.assertFalse(E.matches(ordinary, shlex.join(command), str(self.ws)))

    def test_case_memory_does_not_become_shared_memory(self):
        cid = self.st.append_candidate({"text": "この案件は敬体", "source": "user-stated"})
        self.st.approve(cid)
        p = self.st.read_profile()["preferences"][0]
        self.assertEqual(p["scope"], "workspace")
        self.assertIn("この案件は敬体", build.build(self.st)[0])
        self.st.set_workspace(str(self.root / "project-b"))
        self.assertNotIn("この案件は敬体", build.build(self.st)[0])

    def test_remember_skill_keeps_shell_syntax_as_literal_text(self):
        marker = self.ws / "must-not-exist"
        text = f'説明中の $(touch {marker}) と `backticks` は文字列'
        self.user('/remember ' + text)
        result = self.cli('remember', '--from-user-input')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.st.read_profile()['preferences'][0]['text'], text)
        self.assertFalse(marker.exists())

    def test_global_memory_requires_actual_explicit_user_intent(self):
        self.user("この案件は敬体にして")
        with self.assertRaises(store.UserError):
            self.st.remember("敬体", global_scope=True, quote="全案件で敬体を覚えて")
        with self.assertRaises(store.UserError):
            self.st.remember("敬体", global_scope=True, quote="この案件は敬体にして")
        self.user("全案件で「結論から説明する」を覚えて")
        self.st.remember("結論から説明する", global_scope=True, quote="全案件で「結論から説明する」を覚えて")
        self.st.set_workspace(str(self.root / "project-b"))
        self.assertIn("結論から説明する", build.build(self.st)[0])

    def test_actual_user_intent_overrides_one_matching_operation(self):
        card = self.card()
        quote = "クライアントに急げと言われたので、この版を今すぐ本番へ公開して"
        self.user(quote)
        cmd = "vercel deploy --prod"
        authority.record_override(self.st, card, "Bash", {"command": cmd}, quote)
        def pre(command):
            return self.hook("pre-tool", "PreToolUse", tool_name="Bash", tool_input={"command": command})[0]
        self.assertEqual(pre("vercel deploy --prod --scope other").decision, "ask")
        self.assertEqual(pre(cmd).decision, "allow")
        self.assertEqual(pre(cmd).decision, "ask")
        self.assertEqual(self.st.read_profile()["preferences"], [])
        self.assertEqual(card.risk, "R1")

    def test_quoted_document_or_negative_instruction_cannot_create_global_memory(self):
        for quote in ("資料に『全案件で敬体を覚えて』と書いてある", "全案件で敬体を覚えてほしくない", "全案件で敬体を覚えてと言ったらどうなる？"):
            self.user(quote)
            with self.assertRaises(store.UserError):
                self.st.remember("敬体", global_scope=True, quote=quote)

    def test_local_exception_does_not_remove_global_memory(self):
        quote = "全案件で「敬体で書く」を覚えて"
        self.user(quote)
        pid = self.st.remember("敬体で書く", key="style", global_scope=True, quote=quote)
        cid = self.st.append_candidate({"text": "常体で書く", "key": "style", "source": "user-stated"})
        with self.assertRaises(store.UserError):
            self.st.approve(cid, supersedes=pid)
        self.st.approve(cid)
        text, _ = build.build(self.st)
        self.assertIn("常体で書く", text)
        self.assertNotIn("敬体で書く", text)
        self.st.set_workspace(str(self.root / "other-project"))
        text, _ = build.build(self.st)
        self.assertIn("敬体で書く", text)

    def test_polite_memory_request_and_a_negative_rule_are_valid(self):
        for text, quote in [("結論から説明する", "全案件で「結論から説明する」を覚えておいてくれる？"),
                            ("秘密情報は保存しない", "全案件で「秘密情報は保存しない」を覚えて")]:
            self.user(quote)
            pid = self.st.remember(text, global_scope=True, quote=quote)
            self.assertTrue(pid)

    def test_new_user_message_expires_old_operation_grant(self):
        card = self.card()
        self.user("この版を公開して")
        authority.record_override(self.st, card, "Bash", {"command": "vercel deploy --prod"}, "この版を公開して")
        self.user("やっぱり一旦待って")
        out, _ = self.hook("pre-tool", "PreToolUse", tool_name="Bash", tool_input={"command": "vercel deploy --prod"})
        self.assertEqual(out.decision, "ask")

    def test_encouragement_and_status_do_not_revoke_user_intent(self):
        card = self.card()
        quote = "この版を今すぐ公開して"
        self.user(quote)
        authority.record_override(self.st, card, "Bash", {"command": "vercel deploy --prod"}, quote)
        for status in ("がんばれ", "がんば", "いける？", "再開"):
            self.user(status)
            self.assertEqual(self.st.user_input()['prompt'], quote)
        out, _ = self.hook("pre-tool", "PreToolUse", tool_name="Bash", tool_input={"command": "vercel deploy --prod"})
        self.assertEqual(out.decision, 'allow')
        with self.assertRaises(store.UserError):
            authority.user_quote(self.st, 'がんばれ')

    def test_resume_after_cancellation_is_a_new_instruction(self):
        self.user('公開しないで')
        before = self.st.user_input()['id']
        self.user('再開')
        self.assertNotEqual(self.st.user_input()['id'], before)
        self.assertEqual(self.st.user_input()['prompt'], '再開')

    def test_user_override_for_one_external_send(self):
        card = self.card()
        quote = "この内容を指定の宛先に送信して"
        self.user(quote)
        tool, data = "mcp__example__send_message", {"to": "test@example.invalid", "body": "Draft"}
        out, _ = self.hook("pre-tool", "PreToolUse", tool_name=tool, tool_input=data)
        self.assertEqual(out.decision, "ask")
        authority.record_override(self.st, card, tool, data, quote)
        out, _ = self.hook("pre-tool", "PreToolUse", tool_name=tool, tool_input=data)
        self.assertEqual(out.decision, "allow")
        out, _ = self.hook("pre-tool", "PreToolUse", tool_name=tool, tool_input={**data, "to": "other@example.invalid"})
        self.assertEqual(out.decision, "ask")

    def test_stop_instruction_cannot_authorize_publication(self):
        card = self.card()
        self.user("公開しないで")
        with self.assertRaises(store.UserError):
            authority.record_override(self.st, card, "Bash", {"command": "vercel deploy --prod"}, "公開しないで")

    def test_model_cannot_call_the_hook_entrypoint_as_a_tool(self):
        command = f"python3 {store.REPO_ROOT}/core/ctx/cli.py hook user-input --env codex"
        self.assertEqual(gate.guard("Bash", {"command": command}, str(self.ws))[0], "deny")
        self.assertEqual(gate.guard("PowerShell", {"command": "& " + command + "; echo done"}, str(self.ws))[0], "deny")
        ordinary = f'python3 {store.REPO_ROOT}/core/ctx/cli.py task new --goal hook'
        self.assertEqual(gate.guard("Bash", {"command": ordinary}, str(self.ws))[0], "allow")

    def test_searching_for_deploy_does_not_request_deployment_permission(self):
        self.assertEqual(gate.guard("Bash", {"command": "rg deploy docs"}, str(self.ws))[0], "allow")

    def test_powershell_recovery_and_reads_with_unread_constraints(self):
        self.card()
        c = taskcard.load(self.st, "auth")
        c.constraints.append("公開前に利用者指示を確認する")
        taskcard.save(self.st, c, ["constraint"])
        self.assertTrue(build.needs_context(self.st))
        prefix = "& " + " ".join("'" + str(arg).replace("'", "''") + "'" for arg in
                                  (sys.executable, "-B", store.REPO_ROOT / "core/ctx/cli.py"))
        cases = [(prefix + " context required --sid launch-a", "metadata"),
                 (prefix + " task defer auth --reason unverified --sid launch-a", "metadata"),
                 ("Get-Content -LiteralPath README.md", "read"),
                 ('rg -n "release|deploy" README.md', "read"),
                 ("Select-String -Pattern 'rm -rf /|deploy' -Path README.md", "read")]
        for command, effect in cases:
            for host, tool, key in (("codex", "exec_command", "cmd"), ("claude-code", "Bash", "command")):
                with self.subTest(command=command, host=host):
                    out, _ = self.hook("pre-tool", "PreToolUse", env=host, tool_name=tool, tool_input={key: command})
                    self.assertEqual(E.effect(tool, {key: command}, str(self.ws)), effect)
                    self.assertEqual(out.decision, "allow", out.reason)
        out, _ = self.hook("pre-tool", "PreToolUse", tool_name="PowerShell",
                           tool_input={"command": "Set-Content result.txt changed"})
        self.assertEqual(out.decision, "deny")
        self.assertEqual(self.cli("context", "required").returncode, 0)
        self.assertFalse(build.needs_context(self.st))
        self.assertEqual(self.cli("task", "defer", "auth", "--reason", "実ホスト試験待ち").returncode, 0)
        self.assertEqual(taskcard.load(self.st, "auth").status, "deferred")

    def test_shell_composition_and_untrusted_programs_are_never_read_or_metadata(self):
        prefix = shlex.join([sys.executable, str(store.REPO_ROOT / "core/ctx/cli.py")])
        for command in ('Get-Content README.md | Set-Content copy.txt',
                        'rg "release|deploy" README.md > result.txt',
                        'Get-Content README.md; Remove-Item result.txt',
                        'Get-Content README.md && echo done', 'Get-Content README.md\necho done',
                        'Get-Content "$(Remove-Item x)"', 'Get-Content "`Remove-Item x`"',
                        'Get-Content ${path}', 'Get-Content README.md &',
                        'rg --pre python pattern README.md', 'git diff --output=changed.txt',
                        'git diff --ext-diff',
                        prefix + ' context required; echo changed',
                        prefix + ' verify run -- python -c "print(1)"',
                        'imposter "' + str(store.REPO_ROOT / 'core/ctx/cli.py') + '" context required',
                        prefix + ' hook user-input --env codex', 'kiseki-da-imposter context required'):
            with self.subTest(command=command):
                self.assertNotIn(E.effect("PowerShell", {"command": command}, str(self.ws)), {"read", "metadata"})

    def test_shell_operators_and_cmd_inputs_have_distinct_evidence(self):
        cwd = str(self.ws)
        self.assertNotEqual(E.identity("Bash", {"command": "cat a | cat b"}, cwd),
                            E.identity("Bash", {"command": "cat a '|' cat b"}, cwd))
        self.assertEqual(E.identity("exec_command", {"cmd": "rg pattern README.md"}, cwd),
                         E.identity("Bash", {"command": "rg pattern README.md"}, cwd))

    def test_managed_launcher_requires_runtime_and_both_saved_hashes(self):
        import hashlib
        home = self.st.home
        runtime = home / "runtime/test"
        selected = runtime / "plugins/kiseki-da/core/ctx"
        selected.mkdir(parents=True)
        for filename in ("cli.py", "evidence.py"):
            (selected / filename).write_bytes((store.REPO_ROOT / "core/ctx" / filename).read_bytes())
        bootstrap = home / "bin/kiseki-da.py"
        bootstrap.parent.mkdir()
        bootstrap.write_text("# fixture bootstrap")
        launcher = home / "bin/kiseki-da.cmd"
        launcher.write_text("@echo off\nfixture")
        records = [{"path": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                   for p in (bootstrap, launcher)]
        (home / "current.json").write_text(json.dumps({"runtime": str(runtime)}))
        (home / "install.json").write_text(json.dumps({"management_launchers": records}))
        with patch.object(E.shutil, "which", return_value=str(launcher)):
            self.assertEqual(E.effect("Bash", {"command": "kiseki-da context required"}), "metadata")
            self.assertEqual(gate.guard("Bash", {"command": "kiseki-da hook user-input"}, str(self.ws))[0], "deny")
            self.assertEqual(E.effect("Bash", {"command": "kiseki-da update --yes"}), "unknown")
            bootstrap.write_text("# changed after installation")
            self.assertEqual(E.effect("Bash", {"command": "kiseki-da context required"}), "unknown")

    def test_search_text_is_not_an_operation_but_actual_operations_stay_guarded(self):
        for command in ('rg -n "cat .env|rm -rf /|deploy" README.md',
                        'Write-Output "release deploy delete"', 'git commit -m "release fix"',
                        'git checkout production', 'Get-Content docs/deploy.md'):
            self.assertEqual(gate.guard("PowerShell", {"command": command}, str(self.ws)), ("allow", ""), command)
        for command in ('Get-Content .env', 'rg -n token .env', 'rg -f .env README.md',
                        "Select-String -Path .env -Pattern token", "sls -Pattern token -LiteralPath .env",
                        'Remove-Item C:\\ -Recurse -Force', 'git push -f origin main'):
            self.assertEqual(gate.guard("exec_command", {"cmd": command}, str(self.ws))[0], "deny", command)
        for command in ('vercel deploy --prod', 'npm publish', 'stripe payment create', 'psql -c "DROP TABLE x"'):
            self.assertEqual(gate.guard("PowerShell", {"command": command}, str(self.ws))[0], "ask", command)

    def test_r1_warns_once_without_claiming_completion_on_both_hosts(self):
        c = self.card()
        for host in ("codex", "claude-code"):
            # Different session IDs exercise both host output contracts independently.
            self.st.sid = "advisory-" + host
            taskcard.save(self.st, c, ["note"])
            out, hi = self.hook("stop", "Stop", env=host)
            output = json.loads(hooks.format_output(hi, out)[0])
            self.assertIn("systemMessage", output)
            self.assertNotIn("decision", output)
            self.assertIn("auth", output["systemMessage"])
            self.assertEqual(taskcard.load(self.st, "auth").status, "open")
            self.assertTrue(taskcard.missing_evidence(self.st, c))
            second, hi = self.hook("stop", "Stop", env=host)
            self.assertEqual(hooks.format_output(hi, second)[0], "")

    def test_constraints_cover_all_cards_and_ignore_update_order(self):
        for i in range(4):
            c = taskcard.new_card(self.st, "条件", id=f"constraint-{i}")
            c.constraints.append(f"条件{i}")
            taskcard.save(self.st, c, ["constraint"])
        before = build.required_context(self.st)
        for i in range(4):
            self.assertIn(f"条件{i}", before["text"])
        c = taskcard.load(self.st, "constraint-0")
        taskcard.save(self.st, c, ["note"])
        self.assertEqual(build.required_context(self.st)["hash"], before["hash"])

    def test_metrics_do_not_call_an_unanswered_question_useful(self):
        card = self.card()
        taskcard.add_question(self.st, card, "Which one?")
        taskcard.add_note(self.st, card, "No user answer yet")
        ref = self.st.append_event({"type": "error", "message": "not evidence"})
        taskcard.set_evidence(self.st, card, "C1", ref)
        data = report.week(self.st)
        self.assertIsNone(data["questions_useful_ratio"])
        self.assertEqual(data["questions_followed_by_update_ratio"], 1.0)
        self.assertEqual(data["evidence_reference_ratio"], 1.0)
        self.assertEqual(data["evidence_fill_ratio"], 0.0)

    def test_approval_retry_recovers_after_profile_write(self):
        cid = self.st.append_candidate({"text": "Preference", "source": "user-stated"})
        with patch.object(self.st, "set_candidate_status", side_effect=OSError("fault")):
            with self.assertRaises(OSError):
                self.st.approve(cid)
        self.assertEqual(len(self.st.read_profile()["preferences"]), 1)
        self.st.approve(cid)
        self.assertEqual(len(self.st.read_profile()["preferences"]), 1)
        self.assertEqual(self.st.candidates()[0]["status"], "approved")

    def test_approval_retry_recovers_after_candidate_status_write(self):
        cid = self.st.append_candidate({"text": "Preference", "source": "user-stated"})
        original = self.st.append_event
        def fail_approval(event):
            if event["type"] == "approval":
                raise OSError("fault")
            return original(event)
        with patch.object(self.st, "append_event", side_effect=fail_approval):
            with self.assertRaises(OSError):
                self.st.approve(cid)
        self.st.approve(cid)
        self.assertEqual(len(self.st.read_profile()["preferences"]), 1)
        self.assertEqual(len(list(self.st.iter_events(types={"approval"}))), 1)

    def test_user_prompt_payloads_are_supported_without_context_injection(self):
        for env, event in [("codex", "UserPromptSubmit"), ("claude-code", "UserPromptSubmit")]:
            out, hi = self.hook("user-input", event, env=env, prompt="実際のユーザー発言")
            self.assertEqual(hooks.format_output(hi, out), ("", "", 0))
            self.assertEqual(self.st.user_input()["prompt"], "実際のユーザー発言")
