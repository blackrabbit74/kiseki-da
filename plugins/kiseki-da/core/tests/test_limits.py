"""Structural limits for the public Kiseki DA runtime package."""
from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import re
import sys
import unittest

from core.ctx import store as S


ROOT = Path(__file__).resolve().parents[2]
CTX_DIR = ROOT / "core" / "ctx"
POLICY = ROOT / "core" / "policy" / "interaction.md"
MAX_FILES = 60
MAX_CTX_MODULES = 12
MAX_POLICY_LINES = 60
MAX_POLICY_TOKENS = 800
NORMALIZED = {"user-input", "session-start", "pre-tool", "post-tool", "stop", "session-end"}
HOOK_MAP = {
    "UserPromptSubmit": "user-input",
    "SessionStart": "session-start",
    "PreToolUse": "pre-tool",
    "PostToolUse": "post-tool",
    "PostToolUseFailure": "post-tool",
    "Stop": "stop",
    "SessionEnd": "session-end",
}


def runtime_files() -> list[str]:
    out = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts or "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        out.append(path.relative_to(ROOT).as_posix())
    return sorted(out)


counted_files = runtime_files


def event_types_without_writer() -> list[str]:
    source = "\n".join(path.read_text(encoding="utf-8") for path in sorted(CTX_DIR.glob("*.py")))
    return [name for name in sorted(S.EVENT_TYPES)
            if name not in S.LOG_TYPES and not re.search(r'"type"\s*:\s*"%s"' % re.escape(name), source)]


class LimitsTestCase(unittest.TestCase):
    def test_runtime_file_budget_and_no_junk(self):
        files = runtime_files()
        self.assertLessEqual(len(files), MAX_FILES, files)
        self.assertFalse(any(Path(name).name == ".DS_Store" for name in files), files)

    def test_policy_and_module_limits(self):
        text = POLICY.read_text(encoding="utf-8")
        self.assertLessEqual(len(text.splitlines()), MAX_POLICY_LINES)
        self.assertLessEqual(S.estimate_tokens(text), MAX_POLICY_TOKENS)
        self.assertLessEqual(len(list(CTX_DIR.glob("*.py"))), MAX_CTX_MODULES)

    def test_stdlib_only(self):
        bad = []
        for path in sorted((ROOT / "core").rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [alias.name.split(".")[0] for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    names = [node.module.split(".")[0]]
                elif isinstance(node, ast.ImportFrom) and node.level:
                    bad.append(f"{path}: relative import")
                    continue
                else:
                    continue
                for name in names:
                    if name not in sys.stdlib_module_names and name != "core":
                        bad.append(f"{path}: {name}")
        self.assertEqual(bad, [])

    def test_plugin_hooks_cover_exact_normalized_set(self):
        for filename in ("hooks/hooks.json", "hooks/claude-code.json"):
            path = ROOT / filename
            data = json.loads(path.read_text(encoding="utf-8"))
            names = set(data["hooks"])
            self.assertFalse(names - set(HOOK_MAP), filename)
            self.assertEqual({HOOK_MAP[name] for name in names}, NORMALIZED, filename)
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("/Users/", text)

    def test_event_types_have_writers(self):
        self.assertEqual(event_types_without_writer(), [])


if __name__ == "__main__":
    unittest.main()
