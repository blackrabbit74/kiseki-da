from __future__ import annotations

import os
import shlex
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from installer import hosts
from installer.util import InstallerError


class HostDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.app_cli = self.root / "Applications 日本語 space" / "ChatGPT.app/Contents/Resources/codex"
        self.app_cli.parent.mkdir(parents=True)
        self.app_cli.write_text("test executable", encoding="utf-8")
        self.app_cli.chmod(0o755)
        for patch in (
            mock.patch.dict(os.environ, {"KISEKI_DA_CODEX_COMMAND": "", "KISEKI_DA_CLAUDE_COMMAND": ""}),
            mock.patch.object(hosts.sys, "platform", "darwin"),
            mock.patch.object(hosts, "_codex_app_candidates", return_value=[self.app_cli]),
            mock.patch.object(hosts.shutil, "which", return_value=None),
        ):
            patch.start()
            self.addCleanup(patch.stop)

    def test_explicit_command_takes_precedence_and_keeps_arguments(self):
        # The configured command must never be silently replaced, even if its path is absent.
        configured = '"/explicit path/codex" --config test=true'
        with mock.patch.dict(os.environ, {"KISEKI_DA_CODEX_COMMAND": configured}):
            self.assertEqual(hosts._executable("codex"), shlex.split(configured, posix=os.name != "nt"))

    def test_path_command_takes_precedence_over_app(self):
        with mock.patch.object(hosts.shutil, "which", return_value="/cli/bin/codex"):
            self.assertEqual(hosts._executable("codex"), ["/cli/bin/codex"])

    def test_app_only_mac_uses_absolute_executable_without_changing_path(self):
        before = os.environ.get("PATH")
        manager = hosts.HostManager("codex")
        self.assertEqual(manager.argv("plugin", "list", "--json"),
                         [str(self.app_cli), "plugin", "list", "--json"])
        self.assertEqual(os.environ.get("PATH"), before)

    def test_app_only_preflight_still_validates_python_version_and_plugin_manager(self):
        calls = []
        def run(argv):
            calls.append(argv)
            output = "3.11.16" if argv[0] == "/python3" else "0.153.3" if argv[-1] == "--version" else "marketplace add"
            return subprocess.CompletedProcess(argv, 0, output, "")
        with mock.patch.object(hosts.shutil, "which", side_effect=lambda name: "/python3" if name == "python3" else None), \
                mock.patch.object(hosts, "run_command", side_effect=run):
            if os.name == "nt":
                self.skipTest("Mac preflight invokes POSIX Python discovery")
            result = hosts.HostManager("codex").preflight()
        self.assertEqual(result["executable"], str(self.app_cli.resolve()))
        self.assertIn([str(self.app_cli), "plugin", "--help"], calls)

    def test_missing_or_nonexecutable_candidates_are_skipped(self):
        missing = self.root / "missing/codex"
        with mock.patch.object(hosts, "_codex_app_candidates", return_value=[missing, self.app_cli]), \
                mock.patch.object(hosts.os, "access", return_value=False):
            self.assertEqual(hosts._executable("codex"), ["codex"])

    def test_non_mac_does_not_use_app_fallback(self):
        with mock.patch.object(hosts.sys, "platform", "linux"):
            self.assertEqual(hosts._executable("codex"), ["codex"])

    def test_claude_does_not_use_codex_app(self):
        self.assertEqual(hosts._executable("claude-code"), ["claude"])

    def test_missing_cli_explains_mac_app_discovery(self):
        with mock.patch.object(hosts, "_codex_app_candidates", return_value=[]), \
                mock.patch.object(hosts.Path, "is_file", return_value=False):
            with self.assertRaisesRegex(InstallerError, "ChatGPT.app / Codex.app"):
                hosts.HostManager("codex").preflight()



if __name__ == "__main__":
    unittest.main()
