from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class WorkspaceCLITests(unittest.TestCase):
    def cli(self, *args):
        return subprocess.run([sys.executable, "-B", str(ROOT / "install.py"), *args],
                              text=True, capture_output=True, cwd=ROOT)

    def test_public_extension_dispatch_and_explicit_export(self):
        for args in (("skills", "list", "explaining"), ("--sid", "cli-test", "skills", "list", "explaining")):
            result = self.cli(*args)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)[0]["name"], "explaining-concepts")
        result = self.cli("persona", "pack")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(json.loads(result.stdout)), 3)
        with tempfile.TemporaryDirectory() as raw:
            export = Path(raw) / "export"
            result = self.cli("skills", "export", "developing-story-worlds", str(export))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(len(list((export / "developing-story-worlds/references").glob("*"))), 3)

    def test_project_answers_dry_run_does_not_create_destination(self):
        with tempfile.TemporaryDirectory() as raw:
            answers = Path(raw) / "answers.json"
            answers.write_text(json.dumps({"name": "main", "goal": "相談する", "scope": "指定した範囲",
                                           "persona": "warm", "role": "main"}))
            dest = Path(raw) / "main"
            result = self.cli("project", "create", str(dest), "--answers", str(answers), "--dry-run")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(len(json.loads(result.stdout)["skills"]), 18)
            self.assertFalse(dest.exists())


if __name__ == "__main__":
    unittest.main()
