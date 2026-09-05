from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "kiseki-da"


class PluginPackageTest(unittest.TestCase):
    def test_unreviewed_background_is_not_distributed(self):
        self.assertFalse((ROOT / "docs" / "background").exists())

    def test_manifests_and_marketplaces(self):
        paths = (
            ROOT / ".agents" / "plugins" / "marketplace.json",
            ROOT / ".claude-plugin" / "marketplace.json",
            PLUGIN / ".codex-plugin" / "plugin.json",
            PLUGIN / ".claude-plugin" / "plugin.json",
            PLUGIN / "hooks" / "hooks.json",
            PLUGIN / "hooks" / "claude-code.json",
        )
        data = {path: json.loads(path.read_text(encoding="utf-8")) for path in paths}
        for path in paths:
            self.assertNotIn("/Users/", path.read_text(encoding="utf-8"))
        versions = {
            data[PLUGIN / ".codex-plugin" / "plugin.json"]["version"],
            data[PLUGIN / ".claude-plugin" / "plugin.json"]["version"],
            data[ROOT / ".claude-plugin" / "marketplace.json"]["version"],
        }
        self.assertEqual(versions, {"0.1.0-beta.1"})
        self.assertNotIn("hooks", data[PLUGIN / ".codex-plugin" / "plugin.json"])
        self.assertEqual(data[PLUGIN / ".claude-plugin" / "plugin.json"]["hooks"],
                         "./hooks/claude-code.json")
        codex_entry = data[ROOT / ".agents" / "plugins" / "marketplace.json"]["plugins"][0]
        self.assertEqual(codex_entry["source"]["path"], "./plugins/kiseki-da")
        self.assertTrue((PLUGIN / "LICENSE").is_file())

    def test_host_specific_hook_command_contracts(self):
        claude = json.loads((PLUGIN / "hooks" / "claude-code.json").read_text(encoding="utf-8"))["hooks"]
        codex = json.loads((PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8"))["hooks"]
        self.assertEqual(set(claude), {"UserPromptSubmit", "SessionStart", "PreToolUse", "PostToolUse", "PostToolUseFailure", "Stop", "SessionEnd"})
        self.assertEqual(set(codex), {"UserPromptSubmit", "SessionStart", "PreToolUse", "PostToolUse", "Stop", "SessionEnd"})
        for groups in claude.values():
            for group in groups:
                for hook in group["hooks"]:
                    self.assertEqual(hook["type"], "command")
                    self.assertEqual(hook["command"], "${user_config.python_executable}")
                    self.assertIsInstance(hook["args"], list)
                    self.assertIn("${CLAUDE_PLUGIN_ROOT}/scripts/hook_entry.py", hook["args"])
        for groups in codex.values():
            for group in groups:
                for hook in group["hooks"]:
                    self.assertEqual(hook["type"], "command")
                    self.assertIn("${PLUGIN_ROOT}/scripts/hook_entry.py", hook["command"])
                    self.assertIn("${PLUGIN_ROOT}/scripts/hook_entry.py", hook["commandWindows"])

    def test_exact_normalized_hook_set(self):
        expected = {"user-input", "session-start", "pre-tool", "post-tool", "stop", "session-end"}
        for filename in ("hooks.json", "claude-code.json"):
            text = (PLUGIN / "hooks" / filename).read_text(encoding="utf-8")
            self.assertEqual({event for event in expected if event in text}, expected)

    def test_hook_wrapper_fails_open(self):
        wrapper = PLUGIN / "scripts" / "hook_entry.py"
        bad = subprocess.run([sys.executable, str(wrapper), "bad", "codex"],
                             text=True, capture_output=True, check=False)
        self.assertEqual((bad.returncode, bad.stdout, bad.stderr), (0, "", ""))

    def test_hook_wrapper_dispatches_both_hosts(self):
        wrapper = PLUGIN / "scripts" / "hook_entry.py"
        cli = PLUGIN / "core" / "ctx" / "cli.py"
        with tempfile.TemporaryDirectory() as raw:
            env = os.environ.copy()
            env["KISEKI_DA_HOME"] = raw
            subprocess.run([sys.executable, str(cli), "init"], env=env, check=True, capture_output=True)
            for host, root_key in (("claude-code", "CLAUDE_PLUGIN_ROOT"), ("codex", "PLUGIN_ROOT")):
                host_env = dict(env)
                host_env[root_key] = str(PLUGIN)
                payload = {"session_id": f"s-{host}", "hook_event_name": "SessionStart",
                           "cwd": str(ROOT), "source": "startup"}
                proc = subprocess.run([sys.executable, str(wrapper), "session-start", host], input=json.dumps(payload),
                                      env=host_env, text=True, capture_output=True)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertIn("Kiseki DA", proc.stdout)

    def test_hook_wrapper_missing_pointer_does_not_create_default_state(self):
        wrapper = PLUGIN / "scripts" / "hook_entry.py"
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            env = os.environ.copy()
            env.pop("KISEKI_DA_HOME", None)
            env["HOME"] = str(base)
            env["KISEKI_DA_POINTER"] = str(base / "missing-location")
            env["PLUGIN_ROOT"] = str(PLUGIN)
            payload = {"session_id": "missing-pointer", "hook_event_name": "SessionStart",
                       "cwd": str(base), "source": "startup"}
            proc = subprocess.run(
                [sys.executable, str(wrapper), "session-start", "codex"], input=json.dumps(payload),
                env=env, text=True, capture_output=True, check=False,
            )
            self.assertEqual((proc.returncode, proc.stdout, proc.stderr), (0, "", ""))
            self.assertFalse((base / ".kiseki-da").exists())


if __name__ == "__main__":
    unittest.main()
