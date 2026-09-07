from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "exploring-ideas" / "SKILL.md"


class PresetSkillTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = SKILL.read_text(encoding="utf-8")
        match = re.fullmatch(r"---\n(?P<frontmatter>.*?)\n---\n(?P<body>.*)", cls.text, re.DOTALL)
        if match is None:
            raise AssertionError("SKILL.md must contain one YAML frontmatter block")
        cls.frontmatter = match.group("frontmatter")
        cls.body = match.group("body")

    def frontmatter_value(self, key: str) -> str:
        match = re.search(rf"^{re.escape(key)}:\s*(.+)$", self.frontmatter, re.MULTILINE)
        self.assertIsNotNone(match, f"missing frontmatter key: {key}")
        return match.group(1).strip().strip('"\'')

    def section(self, heading: str) -> str:
        match = re.search(
            rf"^## {re.escape(heading)}\n(?P<content>.*?)(?=^## |\Z)",
            self.body,
            re.MULTILINE | re.DOTALL,
        )
        self.assertIsNotNone(match, f"missing section: {heading}")
        content = match.group("content").strip()
        self.assertTrue(content, f"empty section: {heading}")
        return content

    def test_frontmatter_and_size_gates(self) -> None:
        self.assertEqual(self.frontmatter_value("name"), SKILL.parent.name)
        description = self.frontmatter_value("description")
        self.assertTrue(description.startswith("Explores "))
        self.assertLessEqual(len(description), 1024)
        self.assertIn(len(description.split()), range(25, 61))
        self.assertLessEqual(len(self.body.split()), 350)
        self.assertLessEqual(len(self.text.splitlines()), 300)

    def test_required_section_order_and_no_empty_sections(self) -> None:
        headings = re.findall(r"^## (.+)$", self.body, re.MULTILINE)
        expected = [
            "Purpose",
            "Deliverable",
            "Inputs",
            "Decision rules",
            "Required procedure",
            "Constraints (set by: operator)",
            "Model notes",
        ]
        self.assertEqual(headings, expected)
        for heading in expected:
            self.section(heading)

    def test_instruction_density_and_count_gates(self) -> None:
        decision_lines = re.findall(r"^- .+$", self.section("Decision rules"), re.MULTILINE)
        constraint_lines = re.findall(
            r"^- .+$", self.section("Constraints (set by: operator)"), re.MULTILINE
        )
        self.assertLessEqual(len(decision_lines) + len(constraint_lines), 12)
        prohibitions = re.findall(
            r"^\s*[-*]?\s*(?:Do not|Don't|Never|Must not)\b",
            self.body,
            re.MULTILINE | re.IGNORECASE,
        )
        self.assertLessEqual(len(prohibitions), 5)
        actionable_lines = [
            line
            for line in self.body.splitlines()
            if re.match(r"^(?:[-*]|\d+\.|Done when:|Stop and report when:|Return |Use )", line)
        ]
        prose_lines = [
            line for line in self.body.splitlines() if line and not line.startswith("#")
        ]
        self.assertGreaterEqual(len(actionable_lines) / len(prose_lines), 0.70)

    def test_conflict_reference_and_model_gates(self) -> None:
        booster = re.compile(
            r"think (?:deeply|carefully|step by step)|"
            r"explore (?:exhaustively|thoroughly)|"
            r"(?:several|multiple) approaches|"
            r"double[- ]check|re-?verify|be (?:maximally )?certain|be conservative",
            re.IGNORECASE,
        )
        self.assertIsNone(booster.search(self.text))
        self.assertNotRegex(self.body, r"\b[GS]\d{3,4}\b")
        self.assertNotIn("## References", self.body)
        model_lines = re.findall(r"^- (Claude|GPT):", self.section("Model notes"), re.MULTILINE)
        self.assertEqual(model_lines, ["Claude", "GPT"])


if __name__ == "__main__":
    unittest.main()
