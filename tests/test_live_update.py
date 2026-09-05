from pathlib import Path
import subprocess
import tempfile
import unittest

from installer.transaction import Transaction
from installer.util import InstallerError


class LiveUpdateTransactionTests(unittest.TestCase):
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
