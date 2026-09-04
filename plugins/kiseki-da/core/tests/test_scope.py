from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from core.ctx import hooks, persona, scope, search, taskcard
from core.ctx.store import Store


class ScopeTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name).resolve()
        self.home = base / "state"
        self.p1 = base / "project-a"
        self.p2 = base / "project-b"
        self.outside = base / "outside"
        for path in (self.p1, self.p2, self.outside):
            path.mkdir(parents=True)
        self.common = Store(home=self.home, sid="common")
        self.common.init()

    @staticmethod
    def _tree(root: Path) -> list[tuple[str, bytes | None]]:
        out = []
        if not root.exists():
            return out
        for path in sorted(root.rglob("*")):
            out.append((path.relative_to(root).as_posix(), path.read_bytes() if path.is_file() else None))
        return out

    def test_missing_registry_defaults_to_user_without_writing(self):
        registry = self.home / scope.REGISTRY_NAME
        self.assertFalse(registry.exists())
        resolved = scope.resolve_scope(self.home, self.outside)
        self.assertTrue(resolved.active)
        self.assertEqual((resolved.mode, resolved.state_home), ("user", self.home))
        self.assertFalse(registry.exists())

    def test_registry_rejects_path_traversal_id(self):
        (self.home / scope.REGISTRY_NAME).write_text(
            '{"schema":1,"mode":"project","projects":[{"id":"../../escape","path":"'
            + str(self.p1).replace('\\', '\\\\') + '"}]}\n', encoding="utf-8")
        with self.assertRaisesRegex(Exception, "UUID"):
            scope.load_registry(self.home)

    def test_project_registry_activation_and_longest_path(self):
        a = scope.add_project(self.home, self.p1)
        nested = self.p1 / "nested"
        nested.mkdir()
        b = scope.add_project(self.home, nested)
        self.assertEqual(scope.load_registry(self.home)["mode"], "project")
        self.assertEqual(scope.resolve_scope(self.home, self.p1 / "src").project_id, a["id"])
        self.assertEqual(scope.resolve_scope(self.home, nested / "src").project_id, b["id"])
        inactive = scope.resolve_scope(self.home, self.outside)
        self.assertFalse(inactive.active)
        self.assertIsNone(inactive.state_home)

    def test_remove_deactivates_but_preserves_state(self):
        row = scope.add_project(self.home, self.p1)
        st = scope.scoped_store(self.home, self.p1, sid="p")
        self.assertIsNotNone(st)
        st.capture("preserve me")
        removed = scope.remove_project(self.home, row["id"])
        self.assertTrue(Path(removed["state_preserved"]).is_dir())
        self.assertFalse(scope.resolve_scope(self.home, self.p1).active)

    def test_effective_profile_and_search_are_isolated(self):
        row1 = scope.add_project(self.home, self.p1)
        scope.add_project(self.home, self.p2)
        common_profile = self.common.read_profile()
        common_profile["identity"]["name"] = "共通利用者"
        self.common.write_profile(common_profile)
        self.common.remember("globalconstraint 固定", kind="constraint")
        self.common.remember("globalpreference 共通", kind="preference")

        a = scope.scoped_store(self.home, self.p1, sid="a")
        b = scope.scoped_store(self.home, self.p2, sid="b")
        self.assertTrue(a.is_project)
        persona.save_persona(a, {"name": "A", "warmth": "warm"}, merge=False)
        persona.save_persona(b, {"name": "B", "warmth": "reserved"}, merge=False)
        pref_id = a.remember("alphaonly preference", kind="preference")
        a.remember("alphaonly fact", kind="fact")
        a.remember("alphaonly goal", kind="goal")
        a.append_candidate({"text": "alphaonly candidate", "source": "user-stated"})
        taskcard.new_card(a, "alphaonly task", id="alpha-task")
        a.capture("alphaonly event")
        b.capture("betaonly event")

        effective = a.read_effective_profile()
        self.assertEqual(effective["identity"]["name"], "共通利用者")
        self.assertEqual(effective["persona"]["name"], "A")
        self.assertIn("globalconstraint 固定", [x["text"] for x in effective["constraints"]])
        self.assertEqual([x["text"] for x in effective["preferences"]],
                         ["globalpreference 共通", "alphaonly preference"])
        self.assertNotEqual(pref_id, "p1")  # global p1 and project ids cannot collide

        ids_a = {h["id"] for h in search.search(a, "alphaonly", k=20, decay=False)}
        self.assertIn("task:alpha-task", ids_a)
        self.assertIn(f"profile:{pref_id}", ids_a)
        self.assertFalse(any("beta" in h["snippet"] for h in search.search(a, "betaonly", k=20)))
        self.assertEqual(search.search(b, "alphaonly", k=20), [])
        self.assertEqual(persona.get_persona(b.read_effective_profile())["name"], "B")
        self.assertEqual(a.project_id, row1["id"])

    def test_project_constraint_is_written_to_common_profile(self):
        scope.add_project(self.home, self.p1)
        project = scope.scoped_store(self.home, self.p1, sid="p")
        pid = project.remember("全案件で守る", kind="constraint")
        self.assertIn(pid, [x["id"] for x in self.common.read_profile()["constraints"]])
        self.assertEqual(project.read_profile()["constraints"], [])

    def test_inactive_hook_is_noop_before_any_write(self):
        scope.add_project(self.home, self.p1)
        before = self._tree(self.home)
        hi = hooks.HookInput(
            env="claude-code", event="session-start", sid="inactive", cwd=str(self.outside),
            transcript_path=None, tool=None, tool_input=None, tool_ok=None,
            tool_output_text=None, source="startup", stop_hook_active=False, raw={},
        )
        out = hooks.handle(Store(home=self.home, sid=hi.sid), hi)
        self.assertIsNone(out.context)
        self.assertEqual(self._tree(self.home), before)

        hi.event = "pre-tool"
        hi.tool = "Bash"
        hi.tool_input = {"command": "rm -rf /"}
        out = hooks.handle(Store(home=self.home, sid=hi.sid), hi)
        self.assertIsNone(out.decision)
        self.assertEqual(self._tree(self.home), before)

    def test_cli_project_registration_and_isolation(self):
        cli = Path(__file__).resolve().parents[1] / "ctx" / "cli.py"
        env = os.environ.copy()
        env["KISEKI_DA_HOME"] = str(self.home)

        def call(cwd: Path, *args: str):
            return subprocess.run([sys.executable, str(cli), *args], cwd=cwd, env=env,
                                  text=True, capture_output=True)

        self.assertEqual(call(self.p1, "project", "add", str(self.p1), "--yes").returncode, 0)
        self.assertEqual(call(self.p1, "project", "add", str(self.p2), "--yes").returncode, 0)
        self.assertEqual(call(self.p1, "capture", "alpha-cli-only").returncode, 0)
        hit = call(self.p1, "search", "alpha-cli-only")
        miss = call(self.p2, "search", "alpha-cli-only")
        self.assertIn("alpha-cli-only", hit.stdout)
        self.assertEqual(miss.stdout, "")
        listed = call(self.p1, "project", "list", "--json")
        self.assertEqual(len(json.loads(listed.stdout)), 2)


if __name__ == "__main__":
    unittest.main()
