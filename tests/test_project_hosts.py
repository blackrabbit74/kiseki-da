from __future__ import annotations

import json
import os
from pathlib import Path
import selectors
import shlex
import subprocess
import sys
import tempfile
import time
import tomllib
import unittest
from unittest import mock

from installer.project_hosts import host_files, visibility_warnings


class ProjectHostFilesTests(unittest.TestCase):
    def test_both_hosts_bind_every_event_to_absolute_workspace_entry(self):
        with tempfile.TemporaryDirectory(prefix="kiseki space 日本語 ") as raw:
            destination = Path(raw)
            entry = destination / ".kiseki/entry.py"
            files = host_files(destination, entry, ["researching-with-sources"])
            codex = json.loads(files[".codex/hooks.json"])["hooks"]
            claude_config = json.loads(files[".claude/settings.local.json"])
            claude = claude_config["hooks"]
            self.assertEqual(len(codex), 6)
            self.assertEqual(len(claude), 7)
            for host, events in (("codex", codex), ("claude-code", claude)):
                for name, groups in events.items():
                    for group in groups:
                        for handler in group["hooks"]:
                            argv = shlex.split(handler["command"])
                            self.assertEqual(argv[:3], [str(Path(sys.executable).resolve()), str(entry.resolve()), "--hook"])
                            self.assertEqual(argv[-1], host)
                            self.assertNotIn("args", handler)
                            self.assertNotIn("PLUGIN_ROOT", handler["command"])
                self.assertEqual(events["SessionEnd"][0]["hooks"][0]["timeout"], 3)
            self.assertFalse(claude_config["enabledPlugins"]["kiseki-da@kiseki-da"])
            config = tomllib.loads(files[".codex/config.toml"])
            self.assertEqual(config["plugins"], {"kiseki-da@kiseki-da": {"enabled": False}})
            self.assertTrue(config["features"]["hooks"])
            self.assertNotIn("state", config.get("hooks", {}))
            self.assertEqual(list(destination.iterdir()), [])

    def test_entry_cannot_point_outside_workspace(self):
        with self.assertRaisesRegex(ValueError, "inside"):
            host_files(Path("/tmp/child"), Path("/tmp/parent/entry.py"), [])

    def test_skill_warning_requires_exact_contents_and_does_not_edit(self):
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            original = base / "source/skills/example"
            candidate = base / "home/.codex/skills/example"
            for folder in (original, candidate):
                folder.mkdir(parents=True)
                (folder / "SKILL.md").write_text("same skill\n", encoding="utf-8")
                (folder / "helper.txt").write_text("same dependency\n", encoding="utf-8")
            with mock.patch("installer.project_hosts.Path.home", return_value=base / "home"):
                warnings = visibility_warnings(base / "source", base / "child")
                self.assertEqual(len(warnings), 1)
                self.assertIn(str(candidate), warnings[0])
                (candidate / "helper.txt").write_text("different dependency\n", encoding="utf-8")
                self.assertEqual(visibility_warnings(base / "source", base / "child"), [])
                self.assertEqual((candidate / "helper.txt").read_text(), "different dependency\n")


@unittest.skipUnless(os.environ.get("KISEKI_DA_NATIVE_CODEX"), "Set KISEKI_DA_NATIVE_CODEX to run the native config/skill probe")
class NativeProjectHostTests(unittest.TestCase):
    def _read_native_state(self, host, child):
        (host / "config.toml").write_text(
            '[plugins."kiseki-da@kiseki-da"]\nenabled = true\n[projects.'
            + json.dumps(str(child.resolve())) + ']\ntrust_level = "trusted"\n',
            encoding="utf-8",
        )
        process = subprocess.Popen(
            [os.environ["KISEKI_DA_NATIVE_CODEX"], "app-server", "--stdio", "--strict-config"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, cwd=child, env=dict(os.environ, CODEX_HOME=str(host)),
        )
        def request(rid, method, params):
            process.stdin.write(json.dumps({"jsonrpc": "2.0", "id": rid, "method": method, "params": params}) + "\n")
            process.stdin.flush()
            deadline = time.monotonic() + 15
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                while time.monotonic() < deadline:
                    if not selector.select(1):
                        continue
                    line = process.stdout.readline()
                    if not line:
                        self.fail(f"Native app server closed while reading {method}")
                    message = json.loads(line)
                    if message.get("id") == rid:
                        self.assertNotIn("error", message, message)
                        return message["result"]
            self.fail(f"Native app server timed out reading {method}")
        try:
            request(1, "initialize", {"clientInfo": {"name": "kiseki_child_probe", "version": "0.0.0"}, "capabilities": {"experimentalApi": True}})
            process.stdin.write('{"jsonrpc":"2.0","method":"initialized"}\n')
            process.stdin.flush()
            config = request(2, "config/read", {"cwd": str(child), "includeLayers": True})
            skills = request(3, "skills/list", {"cwds": [str(child)], "forceReload": True})
            return config, skills
        finally:
            process.terminate()
            try:
                process.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()

    def test_generated_config_and_skill_are_loaded_without_model_request(self):
        with tempfile.TemporaryDirectory(prefix="kiseki-native-project-") as raw:
            base = Path(raw)
            host, child = base / "host", base / "child"
            host.mkdir()
            child.mkdir()
            files = host_files(child, child / ".kiseki/entry.py", ["kiseki-child-host-probe"])
            for name, content in files.items():
                target = child / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
            skill = child / ".agents/skills/kiseki-child-host-probe/SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text("---\nname: kiseki-child-host-probe\ndescription: Inspect the disposable child host probe.\n---\nUse the local probe.\n", encoding="utf-8")
            config, skills = self._read_native_state(host, child)
            self.assertFalse(config["config"]["plugins"]["kiseki-da@kiseki-da"]["enabled"])
            self.assertTrue(config["config"]["features"]["hooks"])
            matches = [item for row in skills["data"] for item in row["skills"] if item["name"] == "kiseki-child-host-probe"]
            self.assertEqual(len(matches), 1, skills)
            self.assertEqual(Path(matches[0]["path"]).resolve(), skill.resolve())

    def test_real_main_project_exposes_selected_skills_and_keeps_full_pack_dormant(self):
        from installer.packs import MAIN_SKILLS, skill_catalog
        from installer.projects import create_project

        source = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(prefix="kiseki-native-main-") as raw:
            base = Path(raw)
            host, child = base / "host", base / "child"
            host.mkdir()
            result = create_project(
                source, child, name="Native main probe", goal="Verify host skill discovery",
                scope="Disposable configuration and skill inventory only", persona="concise",
                role="main", skills=None,
            )
            self.assertEqual(result["status"], "created")
            dormant = child / ".kiseki/runtime/packs/skills"
            self.assertEqual(len(list(dormant.glob("*/SKILL.md"))), len(skill_catalog(source)))
            self.assertGreater(len(list(dormant.glob("*/SKILL.md"))), len(MAIN_SKILLS))
            config, skills = self._read_native_state(host, child)
            self.assertFalse(config["config"]["plugins"]["kiseki-da@kiseki-da"]["enabled"])
            workspace = child.resolve()
            local = [item for row in skills["data"] for item in row["skills"]
                     if Path(item["path"]).resolve().is_relative_to(workspace)]
            expected = {name: (child / ".agents/skills" / name / "SKILL.md").resolve()
                        for name in MAIN_SKILLS}
            self.assertEqual(len(local), len(MAIN_SKILLS), [(item["name"], item["path"]) for item in local])
            self.assertEqual({item["name"]: Path(item["path"]).resolve() for item in local}, expected)
            self.assertTrue(all(not Path(item["path"]).resolve().is_relative_to(dormant.resolve()) for item in local))
            self.assertTrue(all(not Path(item["path"]).resolve().is_relative_to((child / ".claude").resolve()) for item in local))


if __name__ == "__main__":
    unittest.main()
