"""Runtime access recovery and bounded guidance across creation and upgrades."""
import contextlib
import errno
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from installer.project_guidance import GUIDANCE, refresh_guidance, render_entry
from installer.projects import create_project, _tree_digest
from installer.packs import MAIN_SKILLS
from installer.runtime_access import check_access, run_with_permission_help
from installer.util import InstallerError


ROOT = Path(__file__).resolve().parents[1]


class RuntimeAccessTests(unittest.TestCase):
    def test_probe_cleans_up_and_leaves_existing_state_untouched(self):
        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw)
            (home / "events.jsonl").write_text("existing\n")
            self.assertEqual(check_access(home)["status"], "writable")
            self.assertEqual(list(home.iterdir()), [home / "events.jsonl"])
            self.assertEqual((home / "events.jsonl").read_text(), "existing\n")

    def test_sandbox_denial_is_diagnosed_even_when_mode_bits_allow_write(self):
        with tempfile.TemporaryDirectory() as raw:
            self.assertTrue(os.access(raw, os.W_OK))
            with mock.patch("installer.runtime_access.tempfile.mkstemp",
                            side_effect=PermissionError(errno.EPERM, "Operation not permitted", raw)):
                result = check_access(raw)
            self.assertEqual(result["status"], "unavailable")
            self.assertIn("ホストの権限確認", result["next"])
            self.assertIn("同じ保存先・引数・--sid", result["next"])

    def test_failure_status_and_stderr_are_preserved_without_automatic_retry(self):
        def failed():
            print("内部エラー: PermissionError: Operation not permitted", file=sys.stderr)
            return 2
        callback = mock.Mock(side_effect=failed)
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            self.assertEqual(run_with_permission_help(callback, "/state"), 2)
        callback.assert_called_once_with()
        self.assertIn("内部エラー:", stderr.getvalue())
        self.assertIn("/state", stderr.getvalue())
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(run_with_permission_help(
                mock.Mock(side_effect=PermissionError("denied")), "/state"), 2)


class ProjectGuidanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="kiseki guidance 日本語 ")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.child = self.base / "child"
        create_project(ROOT, self.child, name="研究", goal="CURRENT_GOAL",
                       scope="CURRENT_SCOPE", persona="concise", skills=list(MAIN_SKILLS[:10]))
        self.entry = self.child / ".kiseki/entry.py"
        self.runtime = self.child / ".kiseki/runtime"
        self.manifest = self.child / ".kiseki/project.json"
        self.env = dict(os.environ, KISEKI_DA_HOME=str(self.base / "other-state"),
                        KISEKI_DA_POINTER=str(self.base / "other-pointer"),
                        PYTHONDONTWRITEBYTECODE="1")

    def cli(self, *args):
        result = subprocess.run([sys.executable, "-B", str(self.entry), "--sid", "guidance-test", *args],
                                cwd=self.child, env=self.env, text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def startup(self, host="codex"):
        result = subprocess.run([sys.executable, "-B", str(self.entry), "--hook", "session-start", host],
                                input=json.dumps({"session_id": "guidance-test", "cwd": str(self.child)}),
                                cwd=self.child, env=self.env, text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"] if host == "codex" else result.stdout

    def legacy(self):
        old = (ROOT / "tests/fixtures/project_entry_beta8.py.txt").read_bytes()
        self.entry.write_bytes(old)
        (self.runtime / "installer/assets/project_entry.py.tmpl").write_bytes(old)
        manifest = json.loads(self.manifest.read_text())
        manifest["runtime"]["sha256"] = _tree_digest(self.runtime)
        self.manifest.write_text(json.dumps(manifest))

    def test_startup_uses_project_cli_and_keeps_guidance_inside_original_budget(self):
        for host in ("codex", "claude-code"):
            text = self.startup(host)
            self.assertEqual(text.count(GUIDANCE), 1)
            self.assertIn(str(self.entry), text)
            self.assertNotIn("core/ctx/cli.py", text)
            self.assertNotIn("__KISEKI_", text)
            self.assertIn("CURRENT_GOAL", text)
            self.assertLessEqual(len(text), 9000)
            ascii_count = sum(ord(c) < 128 for c in text)
            self.assertLessEqual(round(ascii_count / 4 + (len(text) - ascii_count) / 1.6), 2500)
        result = json.loads(self.cli("access", "--json"))
        self.assertEqual(result["home"], str(self.child / ".kiseki/state"))
        self.assertEqual(result["status"], "writable")
        self.assertFalse((self.base / "other-state").exists())

    def test_history_growth_retains_guidance_and_retrieval_under_budget(self):
        self.startup()
        for i in range(12):
            self.cli("task", "new", "--goal", f"HISTORY_{i}_" + "案件の詳細" * 35,
                     "--id", f"history-{i}", "--risk", "R1")
        for _ in range(2):
            text = self.startup()
            self.assertEqual(text.count(GUIDANCE), 1)
            count = sum(ord(c) < 128 for c in text)
            self.assertLessEqual(round(count / 4 + (len(text) - count) / 1.6), 2500)
            self.assertLessEqual(len(text), 9000)
        self.assertIn("HISTORY_0_", self.cli("task", "show", "history-0"))

    def test_context_audit_detects_added_instructions_without_erasing_them(self):
        self.startup()
        self.assertEqual(json.loads(self.cli("context-audit"))["status"], "within_budget")
        instructions = self.child / "AGENTS.md"
        original = "重要な案件の詳細\n" * 1500
        instructions.write_text(original)
        result = subprocess.run([sys.executable, "-B", str(self.entry), "context-audit", "--sid", "guidance-test"],
                                cwd=self.child, env=self.env, text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 2, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["status"], "over_budget")
        self.assertEqual(data["instruction_candidates"][0]["path"], "AGENTS.md")
        self.assertIn("公開スキル", data["unmeasured"])
        self.assertEqual(instructions.read_text(), original)

    def test_legacy_update_is_previewed_backed_up_idempotent_and_inherited(self):
        self.legacy()
        original = self.entry.read_bytes()
        core_hash = _tree_digest(self.runtime / "plugins/kiseki-da/core")
        state_hash = _tree_digest(self.child / ".kiseki/state")
        host_files = {p: p.read_bytes() for p in (self.child / ".codex/hooks.json",
                                                 self.child / ".codex/config.toml",
                                                 self.child / ".claude/settings.local.json")}
        self.assertEqual(refresh_guidance(ROOT, self.child)["status"], "preview")
        self.assertEqual(self.entry.read_bytes(), original)
        result = refresh_guidance(ROOT, self.child, apply=True)
        self.assertEqual(result["status"], "updated")
        self.assertTrue(Path(result["backup"]).is_dir())
        self.assertEqual(refresh_guidance(ROOT, self.child, apply=True)["status"], "unchanged")
        self.assertEqual(_tree_digest(self.runtime / "plugins/kiseki-da/core"), core_hash)
        self.assertEqual(_tree_digest(self.child / ".kiseki/state"), state_hash)
        for path, content in host_files.items():
            self.assertEqual(path.read_bytes(), content)
        self.assertEqual(json.loads(self.manifest.read_text())["runtime"]["sha256"], _tree_digest(self.runtime))
        self.assertIn(GUIDANCE, self.startup())
        self.assertEqual(json.loads(self.cli("access"))["status"], "writable")
        grandchild = self.base / "grandchild"
        create_project(self.runtime, grandchild, name="孫", goal="INHERITED", scope="local",
                       persona="concise", skills=list(MAIN_SKILLS[:10]))
        self.assertEqual((grandchild / ".kiseki/entry.py").read_text(), render_entry(ROOT))

    def test_user_modified_entry_and_runtime_are_preserved(self):
        self.legacy()
        original = self.entry.read_bytes()
        self.entry.write_bytes(original + b"\n# user change\n")
        with self.assertRaisesRegex(InstallerError, "一致しません"):
            refresh_guidance(ROOT, self.child, apply=True)
        self.assertTrue(self.entry.read_bytes().endswith(b"# user change\n"))
        self.entry.write_bytes(original)
        (self.runtime / "user-note.txt").write_text("user change")
        with self.assertRaisesRegex(InstallerError, "hash"):
            refresh_guidance(ROOT, self.child, apply=True)
        self.assertEqual(self.entry.read_bytes(), original)

    def test_partial_update_rolls_back_entry_template_and_manifest(self):
        self.legacy()
        from installer.transaction import Transaction
        before = {p: p.read_bytes() for p in (self.entry, self.manifest,
                                             self.runtime / "installer/assets/project_entry.py.tmpl")}
        with mock.patch.object(Transaction, "write_json", side_effect=OSError("disk failure")):
            with self.assertRaisesRegex(OSError, "disk failure"):
                refresh_guidance(ROOT, self.child, apply=True)
        for path, content in before.items():
            self.assertEqual(path.read_bytes(), content)


if __name__ == "__main__":
    unittest.main()
