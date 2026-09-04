from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class PublicationAuditTest(unittest.TestCase):
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
