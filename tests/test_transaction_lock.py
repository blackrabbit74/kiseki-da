from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class TransactionLockTest(unittest.TestCase):
    def test_second_process_cannot_begin_until_commit(self):
        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw) / "state"
            holder = subprocess.Popen(
                [
                    sys.executable,
                    "-c",
                    (
                        "from pathlib import Path; import sys; "
                        "from installer.transaction import Transaction; "
                        "tx=Transaction(Path(sys.argv[1]), 'holder'); "
                        "print(tx.id, flush=True); sys.stdin.readline(); tx.commit()"
                    ),
                    str(home),
                ],
                cwd=ROOT,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            def cleanup_holder():
                if holder.poll() is None:
                    holder.kill()
                    holder.wait()
                for stream in (holder.stdin, holder.stdout, holder.stderr):
                    if stream is not None and not stream.closed:
                        stream.close()
            self.addCleanup(cleanup_holder)
            self.assertTrue(holder.stdout.readline().strip())
            contender = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    (
                        "from pathlib import Path; import sys; "
                        "from installer.transaction import Transaction; "
                        "tx=Transaction(Path(sys.argv[1]), 'contender'); tx.commit()"
                    ),
                    str(home),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(contender.returncode, 0)
            self.assertIn("別のKiseki DA変更transaction", contender.stderr)
            holder.stdin.write("done\n")
            holder.stdin.flush()
            holder.stdin.close()
            holder.stdin = None
            _, holder_stderr = holder.communicate(timeout=10)
            self.assertEqual(holder.returncode, 0, holder_stderr)
            after = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    (
                        "from pathlib import Path; import sys; "
                        "from installer.transaction import Transaction; "
                        "tx=Transaction(Path(sys.argv[1]), 'after'); tx.commit()"
                    ),
                    str(home),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(after.returncode, 0, after.stderr)

    def test_external_output_is_redacted_and_secret_argv_is_rejected(self):
        from installer.transaction import Transaction
        from installer.util import InstallerError

        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw) / "state"

            def runner(argv):
                return subprocess.CompletedProcess(argv, 0, "Bearer topsecretvalue", "password=hunter2")

            tx = Transaction(home, "redaction")
            tx.external(["manager", "list"], ["manager", "undo"], runner)
            tx.commit()
            journal = json.loads(tx.journal_path.read_text(encoding="utf-8"))
            serialized = json.dumps(journal)
            self.assertNotIn("topsecretvalue", serialized)
            self.assertNotIn("hunter2", serialized)
            self.assertIn("REDACTED", serialized)

            tx = Transaction(home, "secret-argv")
            with self.assertRaises(InstallerError):
                tx.external(["manager", "--token", "topsecretvalue"], None, runner)
            self.assertTrue(tx.rollback(runner))

    def test_resume_recognizes_filesystem_restore_completed_before_crash(self):
        from installer.hosts import run_command
        from installer.transaction import Transaction, rollback_saved

        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw) / "state"
            target = home / "value.txt"
            target.parent.mkdir(parents=True)
            target.write_text("before\n", encoding="utf-8")
            tx = Transaction(home, "crash-resume")
            tx.write_text(target, "after\n")
            tx.commit()
            journal = json.loads(tx.journal_path.read_text(encoding="utf-8"))
            entry = journal["filesystem"][0]
            target.write_bytes(Path(entry["backup"]).read_bytes())
            entry["restore_state"] = "running"
            journal["status"] = "rollback_incomplete"
            tx.journal_path.write_text(json.dumps(journal), encoding="utf-8")
            _, ok, errors = rollback_saved(home, "latest", run_command)
            self.assertTrue(ok, errors)
            self.assertEqual(target.read_text(encoding="utf-8"), "before\n")

    @unittest.skipIf(sys.platform == "win32", "Windows symlink creation requires optional privilege")
    def test_external_symlink_target_is_updated_without_replacing_link(self):
        from installer.hosts import run_command
        from installer.transaction import Transaction, rollback_saved

        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            home = base / "state"
            real = base / "dotfiles" / "settings.json"
            real.parent.mkdir()
            real.write_text("before\n", encoding="utf-8")
            link = base / "config" / "settings.json"
            link.parent.mkdir()
            link.symlink_to(real)
            tx = Transaction(home, "symlink-config")
            tx.write_external_text(link, "after\n")
            tx.commit()
            self.assertTrue(link.is_symlink())
            self.assertEqual(real.read_text(encoding="utf-8"), "after\n")
            _, ok, errors = rollback_saved(home, "latest", run_command)
            self.assertTrue(ok, errors)
            self.assertTrue(link.is_symlink())
            self.assertEqual(real.read_text(encoding="utf-8"), "before\n")

    @unittest.skipIf(sys.platform == "win32", "Windows symlink creation requires optional privilege")
    def test_remove_external_unlinks_symlink_instead_of_target(self):
        from installer.hosts import run_command
        from installer.transaction import Transaction

        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            home = base / "state"
            target = base / "owned-target"
            target.write_text("keep\n", encoding="utf-8")
            link = base / "owned-link"
            link.symlink_to(target)
            tx = Transaction(home, "safe-unlink")
            tx.remove_external(link)
            self.assertFalse(link.exists())
            self.assertTrue(target.is_file())
            self.assertTrue(tx.rollback(run_command))
            self.assertTrue(link.is_symlink())
            self.assertTrue(target.is_file())


if __name__ == "__main__":
    unittest.main()
