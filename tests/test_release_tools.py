from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import subprocess
import sys
import tarfile
import zipfile
import os
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class PublicationAuditTest(unittest.TestCase):
    @unittest.skipIf(os.name == "nt", "symlink checkout requires Windows Developer Mode")
    def test_release_materializes_shared_runtime_from_tracked_snapshot(self):
        with mock.patch.object(sys, "path", [str(ROOT / "tools"), *sys.path]):
            module = load("build_release_materialize", ROOT / "tools" / "build_release.py")
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            repo = base / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            shared = repo / "shared"
            shared.mkdir()
            (shared / "runtime.py").write_text("print('tracked')\n")
            plugin = repo / "plugin"
            plugin.mkdir()
            (plugin / "core").symlink_to("../shared", target_is_directory=True)
            subprocess.run(["git", "add", "."], cwd=repo, check=True)
            subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.com",
                            "-c", "commit.gpgsign=false", "commit", "-qm", "fixture"], cwd=repo, check=True)
            (shared / "runtime.py").write_text("uncommitted\n")
            (shared / "private.txt").write_text("untracked\n")
            archives = [base / "source.zip", base / "source.tar.gz"]
            module.write_archives(repo, archives, "release/")
            first = [p.read_bytes() for p in archives]
            module.write_archives(repo, archives, "release/")
            self.assertEqual(first, [p.read_bytes() for p in archives])
            with zipfile.ZipFile(archives[0]) as bundle:
                self.assertEqual(bundle.read("release/plugin/core/runtime.py"), b"print('tracked')\n")
                self.assertFalse(any("private.txt" in name for name in bundle.namelist()))
                self.assertTrue(all((item.external_attr >> 16) & 0o170000 == 0o100000
                                    for item in bundle.infolist()))
            with tarfile.open(archives[1]) as bundle:
                self.assertTrue(all(item.isfile() for item in bundle.getmembers()))
                self.assertEqual(bundle.extractfile("release/plugin/core/runtime.py").read(), b"print('tracked')\n")
            verifier = load("verify_release_materialize", ROOT / "tools" / "verify_release_assets.py")
            with mock.patch.object(verifier, "ROOT", repo):
                tracked = verifier._tracked()
            self.assertEqual(set(tracked), {"shared/runtime.py", "plugin/core/runtime.py"})
            self.assertEqual(tracked["shared/runtime.py"], tracked["plugin/core/runtime.py"])

    def test_publication_audit_passes(self):
        module = load("publication_audit", ROOT / "tools" / "publication_audit.py")
        result = module.audit()
        self.assertTrue(result["ok"], result["errors"])
        self.assertFalse(result["release_ready"])
        self.assertEqual(result["release_blockers"], ["user_publication_approval"])
        self.assertEqual(module.RELEASE_GATES, ("user_publication_approval",))
        self.assertLessEqual(result["runtime_files"], 60)

    def test_release_ready_requires_every_evidenced_gate(self):
        module = load("publication_audit_gates", ROOT / "tools" / "publication_audit.py")
        baseline = module.audit()
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "gates.json"
            path.write_text(json.dumps({"schema": 1, "version": baseline["version"],
                                        "commit_sha": baseline["commit_sha"],
                                        "tree_sha256": baseline["tree_sha256"], "gates": {
                name: {"passed": True, "evidence": f"evidence/{name}.json"}
                for name in module.RELEASE_GATES
            }}), encoding="utf-8")
            result = module.audit(path)
        self.assertTrue(result["release_ready"], result)

    def test_release_gate_is_bound_to_commit_and_version(self):
        module = load("publication_audit_binding", ROOT / "tools" / "publication_audit.py")
        baseline = module.audit()
        complete = {
            name: {"passed": True, "evidence": f"evidence/{name}.json"}
            for name in module.RELEASE_GATES
        }
        for mutation in ({"commit_sha": "0" * 40}, {"version": "0.0.0"}, {"tree_sha256": "0" * 64}):
            gates = {
                "schema": 1,
                "version": baseline["version"],
                "commit_sha": baseline["commit_sha"],
                "tree_sha256": baseline["tree_sha256"],
                "gates": complete,
            }
            gates.update(mutation)
            with tempfile.TemporaryDirectory() as raw:
                path = Path(raw) / "gates.json"
                path.write_text(json.dumps(gates), encoding="utf-8")
                result = module.audit(path)
            self.assertFalse(result["release_ready"], mutation)
            self.assertEqual(result["release_blockers"], ["release_gates_invalid"])


if __name__ == "__main__":
    unittest.main()
