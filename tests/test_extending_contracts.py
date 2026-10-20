"""docs/EXTENDING.md describes the code as it is: its contract tables are checked against the code.

When this fails after a code change, update docs/EXTENDING.md in the same change.
"""
from __future__ import annotations

import ast
import contextlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "kiseki-da"
CLAUDE_PLUGIN = ROOT / "plugins" / "claude-code" / "kiseki-da"
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


def table_rows(lines: list[str], header_start: str) -> list[list[str]]:
    """Cells of the data rows of the table whose header line starts with `header_start`."""
    start = next(i for i, line in enumerate(lines) if line.startswith(header_start))
    rows = []
    for line in lines[start + 2:]:
        if not line.startswith("|"):
            break
        rows.append([cell.strip() for cell in line.strip("|").split(" | ")])
    return rows


def code(cell: str) -> str:
    return cell.strip().strip("`")


def code_words(cell: str) -> list[str]:
    return re.findall(r"`([^`]+)`", cell)


@contextlib.contextmanager
def isolated_home():
    """A throw-away state home, so no installed launcher or profile on this machine can change a result."""
    with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as cwd:
        old = os.environ.get("KISEKI_DA_HOME")
        os.environ["KISEKI_DA_HOME"] = home
        try:
            yield cwd
        finally:
            if old is None:
                os.environ.pop("KISEKI_DA_HOME", None)
            else:
                os.environ["KISEKI_DA_HOME"] = old


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
        for path in sorted(set(re.findall(r"(?<![\w./-])((?:plugins|core|tests|docs|installer|hooks|acceptance|scripts)/"
                                          r"[\w./-]+\.(?:py|json|md|sh))", text))):
            if not any((base / path).exists() for base in (ROOT, PLUGIN, CLAUDE_PLUGIN)):
                missing_paths.append(path)
        self.assertEqual(missing_paths, [])

    def test_module_table_lists_every_runtime_module(self):
        lines = DOC.read_text(encoding="utf-8").splitlines()
        documented = {code(row[0]) for row in table_rows(lines, "| モジュール | 役割 |")}
        actual = {path.name for path in (PLUGIN / "core" / "ctx").glob("*.py")} - {"__init__.py"}
        self.assertEqual(documented, actual)

    def test_plugin_layout_table_matches_the_tree(self):
        text = DOC.read_text(encoding="utf-8")
        for path in ("plugins/kiseki-da/.codex-plugin/plugin.json", "plugins/kiseki-da/hooks/hooks.json",
                     "plugins/claude-code/kiseki-da/.claude-plugin/plugin.json",
                     "plugins/claude-code/kiseki-da/hooks/claude-code.json"):
            self.assertTrue((ROOT / path).is_file(), path)
        for name in ("core", "scripts", "evals", "state.example", "LICENSE"):
            self.assertIn(f"`{name}`", text)
            self.assertTrue((ROOT / "plugins" / "claude-code" / "kiseki-da" / name).exists(), name)

    def test_secret_rules_stay_last(self):
        # gate.guard() addresses these two rules as _DENY_RE[-1] / _ASK_RE[-1] for its read-only branch.
        from core.ctx import gate
        self.assertTrue(gate.DENY_PATTERNS[-1][1].startswith("秘密情報"), gate.DENY_PATTERNS[-1][1])
        self.assertTrue(gate.ASK_PATTERNS[-1][0].endswith(r"\bsecrets?\b"), gate.ASK_PATTERNS[-1][0])

    def test_guard_examples_match_gate(self):
        from core.ctx import gate
        lines = section("ガード規則")
        rows = table_rows(lines, "| コマンド | 判定 | 決まる手順 |")
        self.assertGreaterEqual(len(rows), 10)
        wrong = []
        with isolated_home() as cwd:
            for row in rows:
                decision = gate.guard("Bash", {"command": code(row[0])}, cwd)[0]
                if decision != row[1]:
                    wrong.append((code(row[0]), row[1], decision))
        self.assertEqual(wrong, [])

    def test_effect_examples_match_evidence(self):
        from core.ctx import evidence
        rows = table_rows(section("ガード規則"), "| コマンド | 分類 |")
        self.assertGreaterEqual(len(rows), 6)
        wrong = []
        with isolated_home() as cwd:
            for row in rows:
                actual = evidence.effect("Bash", {"command": code(row[0])}, cwd)
                if actual != code(row[1].split("（")[0]):
                    wrong.append((code(row[0]), row[1], actual))
        self.assertEqual(wrong, [])

    def test_tool_classes_match_evidence(self):
        from core.ctx import evidence, gate
        lines = section("ガード規則")
        by_class = {row[0]: set(code_words(row[1].split("。")[0]))
                    for row in table_rows(lines, "| 区分 | ツール名 |")}
        shell = next(words for key, words in by_class.items() if key.startswith("シェル"))
        write = next(words for key, words in by_class.items() if key.startswith("書込"))
        self.assertEqual(shell, set(evidence.SHELL_TOOLS))
        self.assertEqual(write, set(evidence.WRITE_TOOLS))
        self.assertEqual(gate._SHELL_TOOLS, evidence.SHELL_TOOLS)
        self.assertEqual(gate._WRITE_TOOLS, evidence.WRITE_TOOLS)
        read_line = next(line for line in lines if line.startswith("1. ツール名が"))
        self.assertEqual(set(code_words(read_line.split("（")[0])), set(evidence.READ_TOOLS))

    def test_effect_table_matches_evidence(self):
        from core.ctx import evidence
        rows = table_rows(section("ガード規則"), "| 分類 | 先頭語 | 補足 |")
        wrong = []
        with isolated_home() as cwd:
            self.assertEqual([code(row[0]) for row in rows[:2]], ["write", "read"])
            for row in rows[:2]:   # the git / python / npm rows are checked below
                for head in code_words(row[1]):
                    actual = evidence.effect("Bash", {"command": f"{head} target"}, cwd)
                    if actual != code(row[0]):
                        wrong.append((head, code(row[0]), actual))
            expected = {"git status": "read", "git diff --output=x": "write", "git diff --ext-diff": "unknown",
                        "python3 -m pytest": "read", "python3 -m unittest": "read", "python3 script.py": "unknown",
                        "npm test": "read", "yarn lint": "read", "npm install": "unknown"}
            for command, effect in expected.items():
                actual = evidence.effect("Bash", {"command": command}, cwd)
                if actual != effect:
                    wrong.append((command, effect, actual))
            for command in ("rg --pre cmd word .",):
                if evidence.effect("Bash", {"command": command}, cwd) != "unknown":
                    wrong.append((command, "unknown"))
        self.assertEqual(wrong, [])

    def test_metadata_table_matches_evidence(self):
        from core.ctx import evidence
        cli_path = PLUGIN / "core" / "ctx" / "cli.py"
        rows = table_rows(section("ガード規則"), "| 先頭の語 | 許可する次の語 |")
        self.assertGreaterEqual(len(rows), 8)

        def is_metadata(*words: str, cwd: str) -> bool:
            command = shlex.join([sys.executable, str(cli_path), *words])
            return evidence.metadata_command(command, cwd)

        problems = []
        with isolated_home() as cwd:
            for first, allowed, *_ in rows:
                subs = code_words(allowed)
                for head in code_words(first):
                    if subs:
                        problems += [(head, sub) for sub in subs if not is_metadata(head, sub, cwd=cwd)]
                        if is_metadata(head, "no-such-subcommand", cwd=cwd):
                            problems.append((head, "no-such-subcommand"))
                    else:
                        problems += [(head, extra) for extra in ([], ["anything"])
                                     if not is_metadata(head, *extra, cwd=cwd)]
            for head in ("approve", "reject", "remember", "capture", "log", "evals"):
                if is_metadata(head, cwd=cwd):
                    problems.append((head, "must not be metadata"))
            for words in (("verify", "run"), ("candidate", "add"), ("session", "clear"), ("project", "list"),
                          ("doctor", "--other")):
                if is_metadata(*words, cwd=cwd):
                    problems.append((*words, "must not be metadata"))
            # global arguments in front are skipped
            if not is_metadata("--home", cwd, "--sid", "s", "--json", "context", "required", cwd=cwd):
                problems.append("global arguments")
        self.assertEqual(problems, [])

    def test_hook_registration_matchers_match_the_files(self):
        bullets = [line for line in section("ホストへの hook 登録") if line.startswith("- ")]
        self.assertEqual(len(bullets), 2)
        for line in bullets:
            path = re.search(r"`(plugins/[^`]+\.json)`", line).group(1)
            hooks_json = json.loads((ROOT / path).read_text(encoding="utf-8"))["hooks"]
            documented = re.search(r"PreToolUse の matcher は `([^`]+)`", line).group(1)
            self.assertEqual(documented, hooks_json["PreToolUse"][0]["matcher"], path)
            if "PostToolUseFailure" in line:
                for event in ("PostToolUse", "PostToolUseFailure"):
                    self.assertEqual(hooks_json[event][0]["matcher"], "*", (path, event))
            else:
                self.assertNotIn("matcher", hooks_json["PostToolUse"][0], path)
        # the mcp branch of gate.guard is documented as unreachable only while no matcher names it
        for path in ("plugins/claude-code/kiseki-da/hooks/claude-code.json", "plugins/kiseki-da/hooks/hooks.json"):
            data = json.loads((ROOT / path).read_text(encoding="utf-8"))["hooks"]
            self.assertNotIn("mcp", data["PreToolUse"][0]["matcher"].lower(), path)

    def test_hook_event_lists_agree(self):
        from core.ctx import cli, hooks
        spec = importlib.util.spec_from_file_location("kiseki_hook_entry", PLUGIN / "scripts" / "hook_entry.py")
        entry = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(entry)
        self.assertEqual(tuple(cli.HOOK_EVENTS), tuple(hooks.EVENTS))
        self.assertEqual(entry.EVENTS, set(hooks.EVENTS))
        self.assertEqual(entry.ENVS, set(cli.ENVS))
        self.assertEqual(set(hooks.EVENT_NAMES), set(cli.ENVS))

    def test_hook_output_table_shows_the_real_shapes(self):
        from core.ctx import hooks
        body = "\n".join(section("hook の出力"))

        def render(env: str, event: str, **out) -> str:
            hi = hooks.HookInput(env=env, event=event, sid="s", cwd="", transcript_path=None, tool=None,
                                 tool_input=None, tool_ok=None, tool_output_text=None, source=None,
                                 stop_hook_active=False, raw={})
            return hooks.format_output(hi, hooks.HookOutput(**out))[0]

        shapes = [
            render("claude-code", "stop", decision="block", reason="<理由>"),
            render("claude-code", "stop", reason="<注意の文>"),
            render("codex", "stop", reason="<注意の文>"),
            render("claude-code", "pre-tool", decision="deny", reason="<理由>"),
            render("codex", "pre-tool", decision="deny", reason="<理由>"),
            render("codex", "session-start", context="<文脈>"),
        ]
        for shape in shapes:
            self.assertTrue(shape and shape in body, shape)
        ask = json.loads(render("claude-code", "pre-tool", decision="ask", reason="<理由>"))["hookSpecificOutput"]
        self.assertEqual((ask["permissionDecision"], ask["permissionDecisionReason"]), ("ask", "<理由>"))
        self.assertIn('"permissionDecision": "ask"', body)
        codex_ask = json.loads(render("codex", "pre-tool", decision="ask", reason="<理由>"))["hookSpecificOutput"]
        self.assertEqual((codex_ask["permissionDecision"], codex_ask["permissionDecisionReason"]),
                         ("deny", hooks.CODEX_ASK_REASON))
        self.assertEqual(render("claude-code", "pre-tool", decision="allow", reason=""), "")
        self.assertEqual(render("claude-code", "stop", reason=""), "")
        self.assertEqual(render("claude-code", "session-start", context="<文脈>"), "<文脈>")


if __name__ == "__main__":
    unittest.main()
