"""Independent project creation, recovery, and copied-runtime integration tests."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from installer import projects
from installer.packs import MAIN_SKILLS
from installer.transaction import Transaction
from installer.util import InstallerError


class ProjectCreationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.destination = self.base / "子の案件 space 日本語"
        self.skills = list(MAIN_SKILLS[:10])
        self.env = dict(os.environ)
        self.env.update({
            "KISEKI_DA_HOME": str(self.base / "unrelated-personal-state"),
            "KISEKI_DA_POINTER": str(self.base / "unrelated-pointer"),
            "PYTHONDONTWRITEBYTECODE": "1",
        })

    def create(self, destination: Path | None = None, **overrides) -> dict:
        options = {
            "name": "調査する子", "goal": "CHILD_RESEARCH_GOAL",
            "scope": "SELECTED_DOCUMENTS_ONLY", "persona": "concise",
            "skills": self.skills,
        }
        options.update(overrides)
        return projects.create_project(ROOT, destination or self.destination, **options)

    def run_entry(self, *args: str, destination: Path | None = None,
                  sid: str = "child-session", cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        root = destination or self.destination
        return subprocess.run(
            [sys.executable, "-B", str(root / ".kiseki/entry.py"), "--sid", sid, *args],
            cwd=cwd or root, env=self.env, text=True, encoding="utf-8",
            capture_output=True, timeout=30, check=False,
        )

    def run_json(self, *args: str, **kwargs):
        result = self.run_entry(*args, "--json", **kwargs)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def hook(self, host: str, *, destination: Path | None = None,
             sid: str = "child-session", payload_cwd: Path | None = None) -> str:
        root = destination or self.destination
        result = subprocess.run(
            [sys.executable, "-B", str(root / ".kiseki/entry.py"), "--hook", "session-start", host],
            input=json.dumps({"session_id": sid, "hook_event_name": "SessionStart",
                              "cwd": str(payload_cwd or root), "source": "startup"}),
            cwd=root, env=self.env, text=True, encoding="utf-8",
            capture_output=True, timeout=30, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        if host == "codex":
            return json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
        return result.stdout

    def pre_tool(self, tool: str, tool_input: dict, *, cwd: Path | None = None) -> dict:
        result = subprocess.run(
            [sys.executable, "-B", str(self.destination / ".kiseki/entry.py"),
             "--hook", "pre-tool", "codex"],
            input=json.dumps({"session_id": "child-session", "hook_event_name": "PreToolUse",
                              "cwd": str(cwd or self.destination), "tool_name": tool,
                              "tool_input": tool_input}),
            cwd=cwd or self.destination, env=self.env, text=True, encoding="utf-8",
            capture_output=True, timeout=30, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout, "pre-tool must emit its denial")
        return json.loads(result.stdout)["hookSpecificOutput"]

    def assert_no_published_project(self, destination: Path | None = None) -> None:
        root = destination or self.destination
        for relative in (".kiseki/runtime", ".kiseki/state", ".kiseki/project.json",
                         ".kiseki/entry.py", ".codex/hooks.json", ".codex/config.toml",
                         ".claude/settings.local.json", "KISEKI.md"):
            self.assertFalse((root / relative).exists(), relative)
        for host in (".agents", ".claude"):
            for skill in self.skills:
                self.assertFalse((root / host / "skills" / skill).exists(), skill)

    def test_dry_run_and_preflight_preserve_existing_files(self) -> None:
        plan = self.create(dry_run=True)
        self.assertEqual(plan["role"], "child")
        self.assertFalse(self.destination.exists())

        for relative in ("KISEKI.md", ".codex/config.toml", ".claude/settings.local.json",
                         ".agents/skills/" + self.skills[0] + "/SKILL.md"):
            with self.subTest(conflict=relative):
                destination = self.base / ("conflict-" + str(len(list(self.base.iterdir()))))
                target = destination / relative
                target.parent.mkdir(parents=True)
                target.write_bytes(b"user-owned\r\n\x00original")
                before = target.read_bytes()
                with self.assertRaises(InstallerError):
                    self.create(destination)
                self.assertEqual(target.read_bytes(), before)
                self.assertFalse((destination / ".kiseki").exists())

    def test_invalid_selections_are_rejected_before_writes(self) -> None:
        available = sorted(path.name for path in (ROOT / "skills").iterdir() if path.is_dir())
        cases = {
            "missing": None,
            "too-few": self.skills[:9],
            "too-many": available[:21],
            "duplicate": [*self.skills[:9], self.skills[0]],
            "traversal": [*self.skills[:9], "../outside"],
            "absolute": [*self.skills[:9], str(self.base / "outside")],
            "not-found": [*self.skills[:9], "nonexistent-selected-skill"],
        }
        for label, selection in cases.items():
            with self.subTest(selection=label):
                with self.assertRaises(InstallerError):
                    self.create(skills=selection)
                self.assertFalse(self.destination.exists())

    def test_invalid_context_requires_real_provenance_before_writes(self) -> None:
        for context in ([{"text": "unattributed"}],
                        [{"text": "bad date", "source": "notes", "date": "2026-99-99"}]):
            with self.subTest(context=context):
                with self.assertRaises(InstallerError):
                    self.create(context=context)
                self.assertFalse(self.destination.exists())

    def test_committed_project_keeps_user_artifacts_and_refuses_recreation(self) -> None:
        self.destination.mkdir()
        user_file = self.destination / "research.md"
        user_file.write_text("User notes remain here.\n", encoding="utf-8")
        self.create()
        manifest = self.destination / ".kiseki/project.json"
        before = manifest.read_bytes()
        with self.assertRaises(InstallerError):
            self.create(goal="replacement")
        self.assertEqual(projects.recover_project(self.destination)["status"], "no_recovery_needed")
        self.assertEqual(manifest.read_bytes(), before)
        self.assertEqual(user_file.read_text(encoding="utf-8"), "User notes remain here.\n")

    def test_manifest_selected_skill_trees_and_main_defaults(self) -> None:
        self.create()
        manifest = json.loads((self.destination / ".kiseki/project.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["role"], "child")
        self.assertEqual(manifest["goal"], "CHILD_RESEARCH_GOAL")
        self.assertEqual([row["name"] for row in manifest["skills"]], self.skills)
        self.assertEqual(manifest["runtime"]["version"], (ROOT / "VERSION").read_text().strip())
        self.assertRegex(manifest["runtime"]["sha256"], r"^[a-f0-9]{64}$")
        for host in (".agents", ".claude"):
            target = self.destination / host / "skills"
            self.assertEqual({path.name for path in target.iterdir()}, set(self.skills))
            for name in self.skills:
                source = ROOT / "skills" / name
                for path in source.rglob("*"):
                    if path.is_file():
                        copied = target / name / path.relative_to(source)
                        self.assertFalse(copied.is_symlink())
                        self.assertEqual(copied.read_bytes(), path.read_bytes())
        main = self.base / "main"
        self.create(main, role="main", skills=None)
        self.assertEqual({path.name for path in (main / ".agents/skills").iterdir()}, set(MAIN_SKILLS))
        self.assertEqual(len(MAIN_SKILLS), 18)

    def test_selected_context_and_custom_persona_reach_both_hooks_without_memory_approval(self) -> None:
        context = [{"text": "CURATED_CONTEXT_ALPHA", "source": "selected-notes.md", "date": "2026-09-06"}]
        persona = {"name": "調査係", "first_person": "私", "verbosity": "compact"}
        self.create(persona=persona, context=context, source_task="parent-plan")
        shown = self.run_json("persona", "show")
        self.assertEqual(shown["name"], persona["name"])
        self.assertEqual(shown["verbosity"], "compact")
        manifest = json.loads((self.destination / ".kiseki/project.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["context"], context)
        self.assertEqual(manifest["source_task"], "parent-plan")
        for host in ("codex", "claude-code"):
            with self.subTest(host=host):
                text = self.hook(host, sid=host + "-session")
                for expected in ("調査係", "CHILD_RESEARCH_GOAL", "SELECTED_DOCUMENTS_ONLY",
                                 "CURATED_CONTEXT_ALPHA", "selected-notes.md", "2026-09-06", ".kiseki/brief.md"):
                    self.assertIn(expected, text)
        brief = (self.destination / ".kiseki/brief.md").read_text(encoding="utf-8")
        for value in context[0].values():
            self.assertIn(value, brief)
        hits = self.run_json("search", "CURATED_CONTEXT_ALPHA", "--kind", "capture")
        self.assertTrue(hits)
        events = [json.loads(line) for line in
                  (self.destination / ".kiseki/state/events.jsonl").read_text(encoding="utf-8").splitlines()]
        captures = [event for event in events if event["type"] == "capture"]
        self.assertEqual(len(captures), 1)
        self.assertEqual(captures[0]["source"], "selected-notes.md (2026-09-06)")
        profile = self.run_json("context", "profile")
        self.assertNotIn("CURATED_CONTEXT_ALPHA", profile["text"])
        self.assertEqual(self.run_json("candidate", "list"), [])
        self.assertFalse(Path(self.env["KISEKI_DA_HOME"]).exists())

    def test_child_task_search_and_evidence_close_use_copied_runtime(self) -> None:
        self.create()
        self.assertTrue(self.hook("codex"))
        nested = self.destination / "research" / "nested"
        nested.mkdir(parents=True)
        made = self.run_json("task", "new", "--goal", "INDEPENDENT_TASK", "--id", "work", cwd=nested)
        self.assertTrue(Path(made["path"]).is_relative_to(self.destination / ".kiseki/state"))
        task = self.run_json("task", "show", "work", cwd=nested)
        self.assertEqual(task["workspace"], str(self.destination))
        hits = self.run_json("search", "INDEPENDENT_TASK", "--kind", "tasks", cwd=nested)
        self.assertEqual([hit["id"] for hit in hits], ["task:work"])
        command = [sys.executable, "-c", "print('copied-runtime-proof')"]
        display = subprocess.list2cmdline(command) if os.name == "nt" else shlex.join(command)
        self.run_json("task", "set", "work", "--add-criterion", "実行が成功する :: " + display)
        premature = self.run_entry("task", "close", "work")
        self.assertNotEqual(premature.returncode, 0)
        verified = self.run_entry("verify", "run", "--", *command, cwd=nested)
        self.assertEqual(verified.returncode, 0, verified.stderr)
        self.assertIn("copied-runtime-proof", verified.stdout)
        bound = self.run_json("task", "set", "work", "--evidence", "C1=last")
        self.assertRegex(bound["criteria"][0]["evidence"], r"^ev:child-session:\d+$")
        self.assertEqual(self.run_json("task", "close", "work")["status"], "done")

    def test_child_states_are_independent_even_for_same_session_and_task_ids(self) -> None:
        child_b = self.base / "child B"
        self.create()
        self.create(child_b, name="B", persona="warm", context=[{
            "text": "ONLY_B_CONTEXT", "source": "B-notes", "date": "2026-09-06",
        }])
        self.hook("codex")
        self.hook("codex", destination=child_b)
        for destination, goal in ((self.destination, "ONLY_A_WORK"), (child_b, "ONLY_B_WORK")):
            self.run_json("task", "new", "--goal", goal, "--id", "same-id", destination=destination)
            self.assertEqual(self.run_json("task", "show", "same-id", destination=destination)["goal"], goal)
        self.assertEqual(self.run_json("search", "ONLY_B_WORK", "--kind", "tasks"), [])
        self.assertEqual(self.run_json("search", "ONLY_A_WORK", "--kind", "tasks", destination=child_b), [])
        self.assertEqual(self.run_json("search", "ONLY_B_CONTEXT", "--kind", "capture"), [])
        self.assertTrue(self.run_json("search", "ONLY_B_CONTEXT", "--kind", "capture", destination=child_b))

    def test_relative_core_write_uses_actual_tool_cwd(self) -> None:
        self.create()
        self.hook("codex")
        core = self.destination / ".kiseki/runtime/plugins/kiseki-da/core"
        original = (core / "ctx/cli.py").read_bytes()
        decision = self.pre_tool("Write", {"file_path": "ctx/cli.py", "content": "replacement"}, cwd=core)
        self.assertEqual(decision["permissionDecision"], "deny")
        self.assertIn("core/", decision["permissionDecisionReason"])
        self.assertEqual((core / "ctx/cli.py").read_bytes(), original)

    def test_entry_rejects_home_abbreviations_and_model_hook_invocation(self) -> None:
        self.create()
        self.hook("codex")
        outside = self.base / "redirected-state"
        for option in ("--home", "--hom", "--ho", "--hom=" + str(outside)):
            with self.subTest(option=option):
                args = [option] if "=" in option else [option, str(outside)]
                result = self.run_entry("init", *args)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(outside.exists())
        result = self.run_entry("hook", "session-start", "--env", "codex")
        self.assertNotEqual(result.returncode, 0)
        entry = self.destination / ".kiseki/entry.py"
        for flag in ("--hook", "hook"):
            with self.subTest(hook=flag):
                command = shlex.join([sys.executable, str(entry), flag, "user-input", "codex"])
                decision = self.pre_tool("Bash", {"command": command})
                self.assertEqual(decision["permissionDecision"], "deny")
                self.assertIn("ホスト専用", decision["permissionDecisionReason"])

    def test_large_initial_context_has_bounded_startup_and_complete_brief(self) -> None:
        context = [{"text": "選定資料" * 125 + f" END_{index}",
                    "source": f"document-{index}.md", "date": "2026-09-06"}
                   for index in range(5)]
        self.create(goal="調査目的" * 200, scope="実施範囲" * 200, context=context)
        for host in ("codex", "claude-code"):
            with self.subTest(host=host):
                text = self.hook(host, sid=host + "-budget")
                self.assertLessEqual(len(text), 9000)
                ascii_chars = sum(ord(char) < 128 for char in text)
                tokens = round(ascii_chars / 4 + (len(text) - ascii_chars) / 1.6)
                self.assertLessEqual(tokens, 2500)
                events = [json.loads(line) for line in
                          (self.destination / ".kiseki/state/events.jsonl").read_text(encoding="utf-8").splitlines()]
                manifest = [event for event in events if event["type"] == "context_manifest"][-1]
                self.assertEqual(manifest["used"], tokens)
                self.assertEqual(manifest["chars"], len(text))
                self.assertIn(".kiseki/brief.md", text)
        brief = (self.destination / ".kiseki/brief.md").read_text(encoding="utf-8")
        for row in context:
            self.assertIn(row["text"], brief)
            self.assertIn(row["source"], brief)

    def test_parent_source_can_disappear_after_copy(self) -> None:
        source = self.base / "配布原本"
        source.mkdir()
        ignore = shutil.ignore_patterns("__pycache__", "*.pyc", ".git")
        for name in ("installer", "plugins", "packs", "skills"):
            shutil.copytree(ROOT / name, source / name, ignore=ignore)
        for name in ("VERSION", "install.py"):
            shutil.copy2(ROOT / name, source / name)
        projects.create_project(source, self.destination, name="copied", goal="SOURCE_INDEPENDENCE",
                                scope="local", persona="concise", skills=self.skills)
        source.rename(self.base / "moved-source")
        shutil.rmtree(self.base / "moved-source")
        self.assertIn("SOURCE_INDEPENDENCE", self.hook("codex"))
        result = self.run_entry("policy", "show", "verification", cwd=self.base)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("証拠", result.stdout)
        self.run_json("task", "new", "--goal", "AFTER_SOURCE_REMOVAL", "--id", "after")
        self.assertEqual(self.run_json("task", "show", "after")["goal"], "AFTER_SOURCE_REMOVAL")

    def test_staging_and_publication_failures_rollback_then_allow_retry(self) -> None:
        for phase in ("stage", "publish"):
            with self.subTest(phase=phase):
                destination = self.base / phase
                destination.mkdir()
                notes = destination / "notes.txt"
                notes.write_text("keep me", encoding="utf-8")
                if phase == "stage":
                    patcher = mock.patch.object(projects, "_runtime_copy", side_effect=OSError("stage failed"))
                else:
                    publish = projects._publish_tree

                    def fail_publish(source, target, tx):
                        if ".agents" in target.parts:
                            raise OSError("publish failed")
                        return publish(source, target, tx)

                    patcher = mock.patch.object(projects, "_publish_tree", side_effect=fail_publish)
                with patcher, self.assertRaises(InstallerError):
                    self.create(destination)
                self.assert_no_published_project(destination)
                self.assertEqual(notes.read_text(encoding="utf-8"), "keep me")
                self.create(destination)
                self.assertTrue((destination / ".kiseki/project.json").is_file())

    def test_crashed_publication_recovers_without_deleting_unrelated_files(self) -> None:
        self.destination.mkdir()
        keep = self.destination / "user-research.txt"
        keep.write_text("survives recovery", encoding="utf-8")
        script = (
            "import os, sys\n"
            "from pathlib import Path\n"
            "from installer import projects\n"
            "from installer.packs import MAIN_SKILLS\n"
            "publish = projects._publish_tree\n"
            "def crash(source, target, tx):\n"
            "    publish(source, target, tx)\n"
            "    if '.agents' in target.parts:\n"
            "        os._exit(73)\n"
            "projects._publish_tree = crash\n"
            "projects.create_project(Path(sys.argv[1]), Path(sys.argv[2]), name='crash',\n"
            "    goal='recover', scope='local', persona='concise', skills=list(MAIN_SKILLS[:10]))\n"
        )
        result = subprocess.run([sys.executable, "-B", "-c", script, str(ROOT), str(self.destination)],
                                cwd=ROOT, env=self.env, text=True, capture_output=True,
                                timeout=60, check=False)
        self.assertEqual(result.returncode, 73, result.stdout + result.stderr)
        self.assertTrue((self.destination / ".kiseki/runtime").is_dir())
        with self.assertRaises(InstallerError):
            self.create()
        recovered = projects.recover_project(self.destination)
        self.assertEqual(recovered["status"], "recovered")
        self.assert_no_published_project()
        self.assertEqual(keep.read_text(encoding="utf-8"), "survives recovery")
        self.create()
        self.assertTrue((self.destination / ".kiseki/project.json").is_file())

    def test_concurrent_nonempty_publication_target_is_preserved(self) -> None:
        rename = projects.os.rename
        conflicted = self.destination / ".agents/skills" / self.skills[0]

        def competing_writer(source, target):
            if Path(target) == conflicted:
                conflicted.mkdir(parents=True)
                (conflicted / "user.txt").write_text("concurrent user data", encoding="utf-8")
            return rename(source, target)

        with mock.patch.object(projects.os, "rename", side_effect=competing_writer):
            with self.assertRaises(InstallerError):
                self.create()
        self.assertEqual((conflicted / "user.txt").read_text(encoding="utf-8"), "concurrent user data")
        with self.assertRaises(InstallerError):
            projects.recover_project(self.destination)
        self.assertEqual((conflicted / "user.txt").read_text(encoding="utf-8"), "concurrent user data")

    def recovery_record(self, journal_id: str, target: Path, victim: Path) -> dict:
        return {
            "schema": 1, "id": journal_id, "action": "project-create", "status": "active",
            "home": str(self.destination / ".kiseki"), "external": [],
            "filesystem": [{"target": str(target), "kind": "absent", "external": True,
                            "backup": None, "value": None,
                            "applied": Transaction._signature(victim)}],
        }

    def test_recovery_rejects_escaped_journal_id_without_touching_external_data(self) -> None:
        victim = self.base / "external-victim.txt"
        victim.write_bytes(b"external data must survive\r\n")
        journal = self.destination / ".kiseki/transactions/valid-id/journal.json"
        journal.parent.mkdir(parents=True)
        escaped = self.destination / ".kiseki/escaped-journal/journal.json"
        escaped.parent.mkdir()
        record = self.recovery_record("../escaped-journal", self.destination / ".." / victim.name, victim)
        journal.write_text(json.dumps(record), encoding="utf-8")
        escaped.write_text(json.dumps({**record, "id": "escaped-journal"}), encoding="utf-8")
        before = {path: path.read_bytes() for path in (victim, journal, escaped)}
        with self.assertRaisesRegex(InstallerError, "transaction ID"):
            projects.recover_project(self.destination)
        for path, content in before.items():
            self.assertEqual(path.read_bytes(), content)

    def test_recovery_rejects_parent_relative_target_before_modifying_journal(self) -> None:
        victim = self.base / "external-victim.txt"
        victim.write_bytes(b"not owned by the project\x00\n")
        journal = self.destination / ".kiseki/transactions/valid-id/journal.json"
        journal.parent.mkdir(parents=True)
        target = self.destination / ".." / victim.name
        journal.write_text(json.dumps(self.recovery_record("valid-id", target, victim)), encoding="utf-8")
        before = journal.read_bytes()
        with self.assertRaisesRegex(InstallerError, "案件外"):
            projects.recover_project(self.destination)
        self.assertEqual(victim.read_bytes(), b"not owned by the project\x00\n")
        self.assertEqual(journal.read_bytes(), before)

    def test_creation_and_recovery_reject_transactions_symlink_before_writes(self) -> None:
        outside = self.base / "external-transactions"
        outside.mkdir()
        sentinel = outside / "user-owned.txt"
        sentinel.write_text("external transaction directory", encoding="utf-8")
        linked = self.destination / ".kiseki/transactions"
        linked.parent.mkdir(parents=True)
        try:
            linked.symlink_to(outside, target_is_directory=True)
        except (NotImplementedError, OSError) as exc:
            self.skipTest(f"This host cannot create directory symlinks: {exc}")
        for operation in (self.create, lambda: projects.recover_project(self.destination)):
            with self.subTest(operation=operation), self.assertRaisesRegex(InstallerError, "symlink"):
                operation()
            self.assertEqual({path.name for path in outside.iterdir()}, {sentinel.name})
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "external transaction directory")
        self.assertTrue(linked.is_symlink())
        self.assert_no_published_project()

    def test_recovery_with_live_transaction_lock_does_not_change_journal(self) -> None:
        tx = Transaction(self.destination / ".kiseki", "project-create")
        try:
            # Recovery would mark this absent reservation restored if it edited
            # the journal before acquiring the live creator's mutation lock.
            tx.backup(self.destination / ".kiseki/runtime")
            before = tx.journal_path.read_bytes()
            with self.assertRaisesRegex(InstallerError, "transaction"):
                projects.recover_project(self.destination)
            self.assertEqual(tx.journal_path.read_bytes(), before)
            self.assertFalse((self.destination / ".kiseki/runtime").exists())
        finally:
            tx.rollback(lambda argv: subprocess.CompletedProcess(argv, 0, "", ""))


if __name__ == "__main__":
    unittest.main()
