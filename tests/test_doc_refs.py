"""Every rationale reference in code and docs must resolve inside the public tree.

Comments once cited section numbers and decision IDs of design documents that are not published, which left
readers who modify the code at a dead end. This test keeps such references out and checks the ones we use.
"""
from __future__ import annotations

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", "build", "__pycache__", ".venv"}
TEXT_SUFFIXES = {".md", ".py", ".json", ".jsonl", ".toml", ".sh", ".txt", ".yml", ".yaml"}

# Section numbers and decision IDs of unpublished design documents. Public docs have no numbered sections and
# docs/DECISIONS.md has no IDs, so any of these is a dead reference: state the reason in place instead.
# The file name itself (`BUILD_BRIEF.md`) is allowed: exclusion and banned-name lists must keep naming it.
DEAD_REFERENCE = re.compile("§|\\bBUILD_" "BRIEF\\b(?!\\.md)|\\b(?:A|AD)-[0-9]+\\b")
# User-visible output is kept byte-identical during the maintainability refactor, so this message keeps its old
# reference until changing CLI output is decided on its own.
ALLOWED_DEAD_REFERENCES = {
    ("plugins/kiseki-da/evals/run.py", 'print("v1 は --dry-run のみ対応しています（BUILD_PLAN §3）", file=sys.stderr)'),
}
PRINCIPLE_REFERENCE = re.compile(r"\bLP-([0-9]+)\b")
MARKDOWN_LINK = re.compile(r"\]\(([^)\s]+)\)")


def text_files() -> list[Path]:
    out = []
    for path in ROOT.rglob("*"):
        if path.is_file() and path.suffix in TEXT_SUFFIXES and not SKIP_DIRS.intersection(path.relative_to(ROOT).parts):
            out.append(path)
    return sorted(out)


def lines_matching(pattern: re.Pattern[str], paths: list[Path],
                   allowed: set[tuple[str, str]] = frozenset()) -> list[tuple[str, int, str]]:
    hits = []
    for path in paths:
        name = path.relative_to(ROOT).as_posix()
        for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if (name, line.strip()) in allowed:
                continue
            for match in pattern.finditer(line):
                hits.append((name, number, match.group(0)))
    return hits


class DocReferenceTest(unittest.TestCase):
    def test_no_references_to_unpublished_documents(self):
        paths = [p for p in text_files() if p != Path(__file__).resolve()]
        self.assertEqual(lines_matching(DEAD_REFERENCE, paths, ALLOWED_DEAD_REFERENCES), [])

    def test_principle_references_exist(self):
        headings = set(re.findall(r"^## (LP-[0-9]+)\b", (ROOT / "docs" / "PRINCIPLES.md").read_text(encoding="utf-8"),
                                  flags=re.M))
        self.assertTrue(headings)
        missing = [hit for hit in lines_matching(PRINCIPLE_REFERENCE, text_files()) if hit[2] not in headings]
        self.assertEqual(missing, [])

    def test_relative_markdown_links_exist(self):
        broken = []
        for path in (p for p in text_files() if p.suffix == ".md"):
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                for target in MARKDOWN_LINK.findall(line):
                    target = target.split("#", 1)[0]
                    if not target or re.match(r"^[a-z][a-z0-9+.-]*:", target):
                        continue
                    if not (path.parent / target).exists():
                        broken.append((path.relative_to(ROOT).as_posix(), number, target))
        self.assertEqual(broken, [])


if __name__ == "__main__":
    unittest.main()
