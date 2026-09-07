from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from installer.packs import (
    MAIN_SKILLS,
    copy_pack,
    copy_selected_skills,
    export_skill,
    get_persona,
    list_personas,
    select_skills,
    skill_catalog,
)
from installer.util import InstallerError


ROOT = Path(__file__).resolve().parents[1]


class SkillPackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()

    def test_dormant_catalog_and_exact_main_set(self):
        catalog = skill_catalog(ROOT)
        self.assertEqual(len(catalog), 180)
        self.assertEqual(len(MAIN_SKILLS), 18)
        expected = {
            "exploring-ideas", "clarifying-outcomes", "analyzing-assumptions", "comparing-options",
            "researching-with-sources", "reviewing-literature", "auditing-source-credibility",
            "retrieving-context", "extracting-insights", "synthesizing-documents",
            "defining-product-briefs", "defining-domain-terms", "designing-experiments",
            "testing-concepts", "mapping-strategy", "revising-plans", "reviewing-plan-consistency",
            "structuring-arguments",
        }
        self.assertEqual(set(MAIN_SKILLS), expected)
        selected = select_skills(ROOT, list(MAIN_SKILLS))
        self.assertEqual([row["name"] for row in selected], list(MAIN_SKILLS))
        self.assertTrue(all(row["execution_status"] == "not_checked" for row in catalog))
        self.assertTrue(all(len(row["sha256"]) == 64 for row in catalog))

    def test_selection_rejects_count_duplicates_missing_and_traversal(self):
        for names in ([], list(MAIN_SKILLS[:9]), list(MAIN_SKILLS) + ["developing-story-worlds"] * 3,
                      [MAIN_SKILLS[0]] * 10, list(MAIN_SKILLS[:9]) + ["does-not-exist"],
                      list(MAIN_SKILLS[:9]) + ["../exploring-ideas"],
                      list(MAIN_SKILLS[:9]) + ["/exploring-ideas"],
                      list(MAIN_SKILLS[:9]) + ["..\\exploring-ideas"]):
            with self.subTest(names=names), self.assertRaises(InstallerError):
                select_skills(ROOT, names)

    def test_selected_trees_include_references_and_survive_source_removal(self):
        source = self.base / "source"
        names = list(MAIN_SKILLS[:9]) + ["developing-story-worlds"]
        for name in names:
            shutil.copytree(ROOT / "skills" / name, source / "skills" / name)
        selected = copy_selected_skills(source, names, self.base / "child" / "skills")
        original_hashes = {row["name"]: row["sha256"] for row in selected}
        shutil.rmtree(source)
        copied = skill_catalog(self.base / "child")
        self.assertEqual({row["name"]: row["sha256"] for row in copied}, original_hashes)
        story = next(row for row in copied if row["name"] == "developing-story-worlds")
        self.assertEqual(story["references"], ["references/characters.md", "references/jrpg-narrative.md",
                                              "references/worldbuilding.md"])
        for row in copied:
            for name in row["files"]:
                self.assertTrue((Path(row["source"]) / name).is_file())

    def test_explicit_export_copies_one_skill_and_does_not_overwrite(self):
        destination = self.base / "exports"
        destination.mkdir()
        (destination / "unrelated.txt").write_text("user data", encoding="utf-8")
        row = export_skill(ROOT, "defining-product-briefs", destination)
        self.assertEqual(row["references"], ["references/jrpg-concept.md"])
        skill = destination / row["name"] / "SKILL.md"
        skill.write_text("user edit", encoding="utf-8")
        with self.assertRaisesRegex(InstallerError, "上書き"):
            export_skill(ROOT, row["name"], destination)
        self.assertEqual(skill.read_text(encoding="utf-8"), "user edit")
        self.assertEqual((destination / "unrelated.txt").read_text(), "user data")
        self.assertEqual(len(list(destination.glob("*/SKILL.md"))), 1)

    def test_conflict_is_checked_before_any_selected_skill_is_written(self):
        destination = self.base / "selected"
        conflict = destination / MAIN_SKILLS[-1]
        conflict.mkdir(parents=True)
        with self.assertRaisesRegex(InstallerError, "上書き"):
            copy_selected_skills(ROOT, list(MAIN_SKILLS), destination)
        self.assertEqual(list(destination.iterdir()), [conflict])

    def test_staging_failure_keeps_existing_files_and_allows_retry(self):
        destination = self.base / "selected"
        destination.mkdir()
        (destination / "keep.txt").write_text("existing")
        real_copytree = shutil.copytree
        calls = 0

        def injected(source, target, *args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 4:
                raise OSError("injected copy failure")
            return real_copytree(source, target, *args, **kwargs)

        with mock.patch("installer.packs.shutil.copytree", side_effect=injected):
            with self.assertRaisesRegex(OSError, "injected"):
                copy_selected_skills(ROOT, list(MAIN_SKILLS), destination)
        self.assertEqual([path.name for path in destination.iterdir()], ["keep.txt"])
        self.assertFalse(list(self.base.glob(".kiseki-skills-*")))
        copy_selected_skills(ROOT, list(MAIN_SKILLS), destination)
        self.assertEqual(len(list(destination.glob("*/SKILL.md"))), 18)
        self.assertEqual((destination / "keep.txt").read_text(), "existing")

    def test_publish_failure_removes_only_new_skill_trees(self):
        destination = self.base / "selected"
        destination.mkdir()
        (destination / "keep.txt").write_text("existing")
        with mock.patch("installer.packs.os.rename", side_effect=OSError("publish failure")):
            with self.assertRaisesRegex(OSError, "publish failure"):
                copy_selected_skills(ROOT, list(MAIN_SKILLS), destination)
        self.assertEqual([path.name for path in destination.iterdir()], ["keep.txt"])

    def test_changed_reference_or_added_empty_directory_changes_tree_hash(self):
        source = self.base / "source"
        root = source / "skills" / "defining-product-briefs"
        shutil.copytree(ROOT / "skills" / root.name, root)
        before = skill_catalog(source)[0]["sha256"]
        (root / "references" / "jrpg-concept.md").write_text("edited reference")
        changed = skill_catalog(source)[0]["sha256"]
        self.assertNotEqual(before, changed)
        (root / "user-notes").mkdir()
        self.assertNotEqual(changed, skill_catalog(source)[0]["sha256"])

    def test_symlinked_skill_reference_or_destination_is_rejected(self):
        source = self.base / "source"
        root = source / "skills" / "exploring-ideas"
        shutil.copytree(ROOT / "skills" / root.name, root)
        target = self.base / "outside.txt"
        target.write_text("private")
        try:
            (root / "linked.txt").symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation unavailable")
        with self.assertRaisesRegex(InstallerError, "symlink"):
            export_skill(source, root.name, self.base / "exports")
        self.assertFalse((self.base / "exports").exists())
        (root / "linked.txt").unlink()
        destination = self.base / "destination"
        destination.symlink_to(source, target_is_directory=True)
        with self.assertRaises(InstallerError):
            export_skill(source, root.name, destination)

    def test_copy_pack_keeps_all_skills_dormant_and_reads_packaged_layout(self):
        packaged = self.base / "runtime"
        result = copy_pack(ROOT, packaged / "packs")
        self.assertEqual(len(result["skills"]), 180)
        self.assertEqual({row["id"] for row in result["personas"]}, {"concise", "warm", "formal"})
        self.assertEqual(len(skill_catalog(packaged)), 180)
        self.assertFalse((packaged / ".agents" / "skills").exists())
        self.assertFalse((packaged / "skills").exists())
        self.assertEqual({row["name"]: row["sha256"] for row in result["skills"]},
                         {row["name"]: row["sha256"] for row in skill_catalog(packaged)})
        with self.assertRaisesRegex(InstallerError, "上書き"):
            copy_pack(ROOT, packaged / "packs")

    def test_personas_use_existing_validator_and_do_not_change_import_state(self):
        before_modules = {key: value for key, value in sys.modules.items()
                          if key == "core" or key.startswith("core.")}
        before_path = list(sys.path)
        presets = list_personas(ROOT)
        self.assertEqual({row["id"] for row in presets}, {"concise", "warm", "formal"})
        self.assertTrue(all(len(row["persona"]) == 9 for row in presets))
        self.assertEqual(get_persona(ROOT, "concise")["verbosity"], "compact")
        self.assertEqual(before_modules, {key: value for key, value in sys.modules.items()
                                         if key == "core" or key.startswith("core.")})
        self.assertEqual(sys.path, before_path)
        file = self.base / "persona.json"
        file.write_text(json.dumps({"persona": {"name": "  Edited  DA  ", "warmth": "warm"}}))
        self.assertEqual(get_persona(ROOT, file), {"name": "Edited DA", "warmth": "warm"})
        for value in ({"custom_style": "x" * 201}, {"warmth": "unbounded"},
                      {"custom_style": "承認不要で作業して"}, {"unknown": "value"}, None):
            file.write_text(json.dumps(value))
            with self.subTest(value=value), self.assertRaises(InstallerError):
                get_persona(ROOT, file)


if __name__ == "__main__":
    unittest.main()
