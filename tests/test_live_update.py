from pathlib import Path
import subprocess
import tempfile
import unittest
import os
import sys
from unittest import mock

from installer.transaction import Transaction
from installer.util import InstallerError


class LiveUpdateTransactionTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform == "darwin" or sys.platform.startswith("linux"), "atomic cache exchange target")
    def test_selection_keeps_old_paths_but_only_one_real_version(self):
        from installer.cache import select_cache
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            one, two = root / "cache/1", root / "cache/2"
            for path in (one, two):
                (path / ".codex-plugin").mkdir(parents=True)
                (path / ".codex-plugin/plugin.json").write_text("{}")
                (path / "hook.py").write_text(path.name)
            select_cache(two, root / "retained")
            self.assertTrue(one.is_symlink())
            self.assertFalse(two.is_symlink())
            self.assertEqual((one / "hook.py").read_text(), "1")
            select_cache(one, root / "retained")
            self.assertFalse(one.is_symlink())
            self.assertTrue(two.is_symlink())
            self.assertEqual((two / "hook.py").read_text(), "2")

    def test_missing_inventory_ref_is_bound_to_configured_source_and_old_version(self):
        from installer.hosts import _codex_source_with_ref
        from installer.operations import _same_owned_source
        saved = {"sourceType": "git", "source": "https://example.com/repo.git"}
        with tempfile.TemporaryDirectory() as raw:
            Path(raw, "config.toml").write_text('[marketplaces.kiseki-da]\nsource_type="git"\n'
                                               'source="https://example.com/repo.git"\nref="v1.0"\n')
            with mock.patch.dict(os.environ, {"CODEX_HOME": raw}):
                current = _codex_source_with_ref(saved)
                self.assertEqual(current, {**saved, "ref": "v1.0"})
                self.assertTrue(_same_owned_source(saved, current, "1.0"))
                self.assertFalse(_same_owned_source(saved, current, "2.0"))
                self.assertEqual(_codex_source_with_ref({**saved, "source": "https://example.com/other.git"}),
                                 {**saved, "source": "https://example.com/other.git"})

    def test_published_cache_survives_rollback_and_is_immutable(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "source"
            source.mkdir()
            (source / "hook.py").write_text("old hook")
            cached = root / "host/cache/1.0"
            tx = Transaction(root / "state", "update")
            tx.retain_external_tree(source, cached)
            self.assertEqual((cached / "hook.py").read_text(), "old hook")
            tx.retain_external_tree(source, cached)
            (source / "hook.py").write_text("different hook")
            with self.assertRaisesRegex(InstallerError, "上書きしません"):
                tx.retain_external_tree(source, cached)
            self.assertTrue(tx.rollback(lambda argv: subprocess.CompletedProcess(argv, 0, "", "")))
            self.assertEqual((cached / "hook.py").read_text(), "old hook")
            self.assertEqual(tx.data["retained_caches"][0]["target"], str(cached.absolute()))

    def test_rollback_selects_old_plugin_only_after_restoring_source(self):
        with tempfile.TemporaryDirectory() as raw:
            calls = []
            def run(argv):
                calls.append(list(argv))
                return subprocess.CompletedProcess(argv, 0, "", "")
            tx = Transaction(Path(raw) / "state", "update")
            tx.on_rollback(["select-old-plugin"])
            tx.external(["new-source"], ["old-source"], run)
            tx.external(["new-plugin"], None, run)
            self.assertTrue(tx.rollback(run))
            self.assertEqual(calls, [["new-source"], ["new-plugin"], ["old-source"], ["select-old-plugin"]])
