from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from installer.packs import MAIN_SKILLS, skill_catalog
from installer.skill_migration import migrate_skills
from installer.util import InstallerError


ROOT = Path(__file__).resolve().parents[1]


class SkillMigrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.visible = self.base / "user" / ".agents" / "skills"
        self.archive = self.base / "archive"

    def install(self, *names):
        for name in names:
            shutil.copytree(ROOT / "skills" / name, self.visible / name)

    def journal(self):
        paths = list(self.archive.glob("*/journal.json"))
        self.assertEqual(len(paths), 1)
        return json.loads(paths[0].read_text())

    def test_dry_run_performs_zero_writes_and_reports_concrete_plan(self):
        self.install("exploring-ideas", "developing-story-worlds")
        before = {str(path): path.stat().st_mtime_ns for path in self.base.rglob("*")}
        result = migrate_skills(ROOT, self.visible, self.archive)
        after = {str(path): path.stat().st_mtime_ns for path in self.base.rglob("*")}
        self.assertEqual(before, after)
        self.assertFalse(self.archive.exists())
        self.assertEqual(result["moved"], [])
        self.assertEqual([row["name"] for row in result["planned"]], ["developing-story-worlds"])
        self.assertEqual(result["preserved"][0]["reason"], "selected")
        self.assertEqual(len(result["already_absent"]), 178)

    def test_full_migration_retains_exact_main_set_and_archives_references(self):
        for row in skill_catalog(ROOT):
            self.install(row["name"])
        result = migrate_skills(ROOT, self.visible, self.archive, dry_run=False)
        self.assertEqual({path.name for path in self.visible.iterdir()}, set(MAIN_SKILLS))
        self.assertEqual(len(result["moved"]), 162)
        self.assertEqual(self.journal()["status"], "committed")
        row = next(item for item in result["moved"] if item["name"] == "developing-story-worlds")
        archived = Path(row["archived_path"])
        self.assertTrue((archived / "references" / "worldbuilding.md").is_file())
        transaction = archived.parent.parent
        self.assertEqual(len(skill_catalog(transaction)), 162)
        self.assertFalse(list(self.visible.glob(".kiseki-migration-*")))
        before = {str(path): path.stat().st_mtime_ns for path in self.archive.rglob("*")}
        rerun = migrate_skills(ROOT, self.visible, self.archive, dry_run=False)
        self.assertEqual(rerun["moved"], [])
        self.assertEqual(len(rerun["already_absent"]), 162)
        self.assertEqual(before, {str(path): path.stat().st_mtime_ns for path in self.archive.rglob("*")})

    def test_modified_added_files_empty_dirs_and_unrelated_entries_are_preserved(self):
        names = ("developing-story-worlds", "developing-python-modules", "developing-go-services")
        self.install(*names)
        (self.visible / names[0] / "SKILL.md").write_text("user edit")
        (self.visible / names[1] / "user-notes.txt").write_text("user notes")
        (self.visible / names[2] / "empty-user-dir").mkdir()
        (self.visible / "user-skill").mkdir()
        (self.visible / "notes.txt").write_text("keep")
        result = migrate_skills(ROOT, self.visible, self.archive, dry_run=False)
        self.assertEqual(result["moved"], [])
        self.assertFalse(self.archive.exists())
        reasons = {row["name"]: row["reason"] for row in result["preserved"]}
        self.assertTrue(all(reasons[name] == "modified" for name in names))
        self.assertEqual(reasons["user-skill"], "not_in_pack")
        self.assertEqual(reasons["notes.txt"], "not_in_pack")
        self.assertEqual((self.visible / names[0] / "SKILL.md").read_text(), "user edit")

    def test_symlinked_and_broken_link_copies_are_preserved(self):
        self.install("developing-story-worlds")
        outside = self.base / "outside.txt"
        outside.write_text("keep")
        try:
            (self.visible / "developing-story-worlds" / "extra.txt").symlink_to(outside)
            (self.visible / "developing-python-modules").symlink_to(self.base / "missing")
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation unavailable")
        result = migrate_skills(ROOT, self.visible, self.archive, dry_run=False)
        self.assertEqual(result["moved"], [])
        self.assertEqual(len(result["preserved"]), 2)
        self.assertTrue((self.visible / "developing-python-modules").is_symlink())
        self.assertEqual(outside.read_text(), "keep")

    def test_archive_and_keep_validation_precedes_writes(self):
        self.install("developing-story-worlds")
        for archive in (Path("relative"), self.visible / "archive", ROOT / "archive",
                        self.base / "user" / ".codex" / "skills" / "archive",
                        self.base / "user" / ".claude" / "skills" / "archive",
                        self.base / "user" / ".codex" / "plugins" / "cache" / "sample" / "1" / "skills" / "archive",
                        self.visible.parent):
            with self.subTest(archive=archive), self.assertRaises(InstallerError):
                migrate_skills(ROOT, self.visible, archive, dry_run=False)
        for keep in (["no-such-skill"], ["../developing-story-worlds"], [MAIN_SKILLS[0]] * 2):
            with self.subTest(keep=keep), self.assertRaises(InstallerError):
                migrate_skills(ROOT, self.visible, self.archive, keep=keep, dry_run=False)
        self.assertFalse(self.archive.exists())
        with self.assertRaisesRegex(InstallerError, "原本"):
            migrate_skills(ROOT, ROOT / "skills", self.archive, dry_run=False)

    def test_copy_failure_restores_all_originals_and_journals_failure(self):
        names = ("developing-python-modules", "developing-story-worlds")
        self.install(*names)
        original = shutil.copytree

        def failing(source, target, *args, **kwargs):
            if Path(source).name == "developing-story-worlds":
                raise OSError("injected second tree failure")
            return original(source, target, *args, **kwargs)

        with mock.patch("installer.skill_migration.shutil.copytree", side_effect=failing):
            with self.assertRaisesRegex(InstallerError, "復元済み"):
                migrate_skills(ROOT, self.visible, self.archive, dry_run=False)
        self.assertEqual({path.name for path in self.visible.iterdir()}, set(names))
        self.assertEqual(self.journal()["status"], "rolled_back")
        actual = {row["name"]: row["sha256"] for row in skill_catalog(self.visible.parent)}
        expected = {row["name"]: row["sha256"] for row in skill_catalog(ROOT) if row["name"] in names}
        self.assertEqual(actual, expected)
        retry = migrate_skills(ROOT, self.visible, self.archive, dry_run=False)
        self.assertEqual(len(retry["moved"]), 2)

    def test_new_visible_entry_is_not_overwritten_by_rollback(self):
        name = "developing-story-worlds"
        self.install(name)

        def conflicting(source, target, *args, **kwargs):
            path = self.visible / name
            path.mkdir()
            (path / "user.txt").write_text("concurrent edit")
            raise OSError("injected conflict")

        with mock.patch("installer.skill_migration.shutil.copytree", side_effect=conflicting):
            with self.assertRaisesRegex(InstallerError, "復元が未完了"):
                migrate_skills(ROOT, self.visible, self.archive, dry_run=False)
        self.assertEqual((self.visible / name / "user.txt").read_text(), "concurrent edit")
        record = self.journal()
        self.assertEqual(record["status"], "rollback_incomplete")
        self.assertTrue((Path(record["holding"]) / name / "SKILL.md").is_file())

    def test_partial_original_cleanup_restores_complete_archive_copy(self):
        name = "developing-story-worlds"
        self.install(name)
        original = shutil.rmtree

        def partial(path, *args, **kwargs):
            path = Path(path)
            if path.name == name and path.parent.name.startswith(".kiseki-migration-"):
                (path / "SKILL.md").unlink()
                raise OSError("partial cleanup failure")
            return original(path, *args, **kwargs)

        with mock.patch("installer.skill_migration.shutil.rmtree", side_effect=partial):
            with self.assertRaisesRegex(InstallerError, "partial cleanup failure"):
                migrate_skills(ROOT, self.visible, self.archive, dry_run=False)
        self.assertEqual((self.visible / name / "SKILL.md").read_bytes(),
                         (ROOT / "skills" / name / "SKILL.md").read_bytes())
        self.assertTrue((self.visible / name / "references" / "worldbuilding.md").is_file())
        self.assertEqual(self.journal()["status"], "rollback_incomplete")


if __name__ == "__main__":
    unittest.main()
