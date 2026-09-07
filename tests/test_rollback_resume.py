from pathlib import Path
import subprocess
import tempfile
import unittest

from installer.transaction import Transaction, rollback_saved


class RollbackResumeTests(unittest.TestCase):
    def interrupted_rollback(self, base):
        home = base / 'state'
        config = base / 'host.toml'
        config.write_text('original\n', encoding='utf-8')
        tx = Transaction(home, 'resume-test')
        tx.track_external_mutable(config)

        def install(argv):
            config.write_text('installed\n', encoding='utf-8')
            return subprocess.CompletedProcess(argv, 0, '', '')

        tx.external(['install'], ['undo'], install)
        failed = lambda argv: subprocess.CompletedProcess(argv, 1, '', 'network unavailable')
        self.assertFalse(tx.rollback(failed))
        self.assertEqual(config.read_text(encoding='utf-8'), 'original\n')
        return home, config, tx.id

    def test_retry_accepts_own_restoration_and_restores_after_native_undo(self):
        with tempfile.TemporaryDirectory() as temp:
            home, config, txid = self.interrupted_rollback(Path(temp))
            called = []

            def undo(argv):
                called.append(argv)
                config.write_text('native undo changed formatting\n', encoding='utf-8')
                return subprocess.CompletedProcess(argv, 0, '', '')

            _, ok, errors = rollback_saved(home, txid, undo)
            self.assertTrue(ok, errors)
            self.assertEqual(called, [['undo']])
            self.assertEqual(config.read_text(encoding='utf-8'), 'original\n')

    def test_retry_still_preserves_user_edit_after_own_restoration(self):
        with tempfile.TemporaryDirectory() as temp:
            home, config, txid = self.interrupted_rollback(Path(temp))
            config.write_text('user edit\n', encoding='utf-8')
            called = []

            def undo(argv):
                called.append(argv)
                return subprocess.CompletedProcess(argv, 0, '', '')

            _, ok, errors = rollback_saved(home, txid, undo)
            self.assertFalse(ok)
            self.assertTrue(errors)
            self.assertEqual(called, [])
            self.assertEqual(config.read_text(encoding='utf-8'), 'user edit\n')

    def test_failed_retry_restores_partial_native_change_and_remains_resumable(self):
        with tempfile.TemporaryDirectory() as temp:
            home, config, txid = self.interrupted_rollback(Path(temp))

            def failed_undo(argv):
                config.write_text('partially changed\n', encoding='utf-8')
                return subprocess.CompletedProcess(argv, 1, '', 'network unavailable')

            _, ok, errors = rollback_saved(home, txid, failed_undo)
            self.assertFalse(ok)
            self.assertTrue(errors)
            self.assertEqual(config.read_text(encoding='utf-8'), 'original\n')
            success = lambda argv: subprocess.CompletedProcess(argv, 0, '', '')
            _, ok, errors = rollback_saved(home, txid, success)
            self.assertTrue(ok, errors)
            self.assertEqual(config.read_text(encoding='utf-8'), 'original\n')


if __name__ == '__main__':
    unittest.main()
