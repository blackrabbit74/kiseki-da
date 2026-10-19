"""docs/EXTENDING.md describes the code as it is: its contract tables are checked against the code.

When this fails after a code change, update docs/EXTENDING.md in the same change.
"""
from __future__ import annotations

import ast
import importlib
from pathlib import Path
import re
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "kiseki-da"
DOC = ROOT / "docs" / "EXTENDING.md"
if str(PLUGIN) not in sys.path:
    sys.path.insert(0, str(PLUGIN))


def section(title: str) -> list[str]:
    lines = DOC.read_text(encoding="utf-8").splitlines()
    start = lines.index(f"### {title}")
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("#")), len(lines))
    return lines[start + 1:end]


def first_column(lines: list[str]) -> list[str]:
    return [m.group(1) for line in lines if (m := re.match(r"^\| `([^`]+)` \|", line))]


def comparable(value):
    return tuple(sorted(value)) if isinstance(value, (set, frozenset)) else value


class ExtendingContractsTest(unittest.TestCase):
    def test_constants_table_matches_code(self):
        rows = [line for line in section("定数一覧") if line.startswith("| `")]
        self.assertGreaterEqual(len(rows), 20)
        wrong = []
        for row in rows:
            cells = [cell.strip() for cell in row.strip("|").split(" | ")]
            module, name = cells[0].strip("`").split(".", 1)
            actual = comparable(getattr(importlib.import_module(f"core.ctx.{module}"), name))
            if ast.literal_eval(cells[1]) != actual:
                wrong.append((cells[0], cells[1], actual))
        self.assertEqual(wrong, [])

    def test_event_type_table_matches_store(self):
        from core.ctx import store
        names = first_column(section("イベント種別（events.jsonl）"))
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(set(names), set(store.EVENT_TYPES))

    def test_week_keys_match_report(self):
        from core.ctx import report
        keys = [m.group(1) for line in section("週次レポートのキー") if (m := re.match(r"^- `([a-z_]+)`:", line))]
        self.assertEqual(tuple(keys), tuple(report.WEEK_KEYS))

    def test_normalized_events_match_hooks(self):
        from core.ctx import hooks
        self.assertEqual(tuple(first_column(section("正規化イベントとホストのイベント名"))), tuple(hooks.EVENTS))

    def test_guard_rule_tables_match_gate(self):
        from core.ctx import gate
        tables: dict[str, list[str]] = {"deny": [], "ask": []}
        current = None
        for line in section("ガード規則"):
            if line.startswith("`DENY_PATTERNS`"):
                current = "deny"
            elif line.startswith("`ASK_PATTERNS`"):
                current = "ask"
            elif current and (m := re.match(r"^\| [0-9]+ \| (.+?) \| ", line)):
                tables[current].append(m.group(1))
        self.assertEqual(tables["deny"], [reason for _, reason in gate.DENY_PATTERNS])
        self.assertEqual(tables["ask"], [reason for _, reason in gate.ASK_PATTERNS])

    def test_runtime_commands_reach_the_launcher(self):
        from core.ctx import cli
        from installer.cli import RUNTIME_COMMANDS
        import argparse
        parser = cli.build_parser()
        action = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
        # `init` is not exposed through the `kiseki-da` launcher; the installer prepares the state directory.
        self.assertEqual(set(action.choices) - {"init"}, set(RUNTIME_COMMANDS))

    def test_named_tests_and_paths_exist(self):
        text = DOC.read_text(encoding="utf-8")
        test_sources = "\n".join(p.read_text(encoding="utf-8") for p in sorted(ROOT.rglob("test_*.py"))
                                 if ".git" not in p.parts)
        missing_tests = sorted({name for name in re.findall(r"`(test_[a-z0-9_]+)`", text)
                                if not re.search(rf"def {name}\b", test_sources)})
        self.assertEqual(missing_tests, [])
        missing_paths = []
        for path in sorted(set(re.findall(r"`((?:core|tests|docs|installer|hooks|acceptance|scripts)/[\w./-]+"
                                          r"\.(?:py|json|md|sh))`", text))):
            if not ((ROOT / path).exists() or (PLUGIN / path).exists()):
                missing_paths.append(path)
        self.assertEqual(missing_paths, [])


if __name__ == "__main__":
    unittest.main()
