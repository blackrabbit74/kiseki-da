#!/usr/bin/env python3
"""Kiseki DA evals runner (v0.1: ``--dry-run`` only).

Lists the template cases in ``cases.jsonl`` next to this file. The execution
body and pass^k are deliberately not implemented (INTERFACES.md §0,
docs/BUILD_PLAN.md §3). The script imports nothing from ``core`` so it can be
run from any cwd on its own; ``cli.py evals run`` only execs it and forwards
the exit code.

Record shape (one JSON object per line, DECISIONS A-21):
    {"id": str, "risk": "R0".."R3", "kind": str, "input": str, "expect": [str]}
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

CASES_PATH = Path(__file__).resolve().parent / "cases.jsonl"
REQUIRED = ("id", "risk", "kind", "input", "expect")
USAGE = (
    "使い方: python3 evals/run.py --dry-run [--json]\n"
    "  --dry-run  ケースを列挙するだけで実行しない（v1 はこれのみ）\n"
    "  --json     ケースを JSON 配列で出力する\n"
    "  -h         この説明を表示する\n"
)
# argparse's English error texts reachable here → Japanese (BUILD_BRIEF §2: CLI text is Japanese only).
# Same wording as cli.py's _ARGPARSE_JA, duplicated because run.py imports nothing from core. With three
# store_true flags and parse_known_args only `--flag=value` reaches error(); an unmatched text keeps the
# `引数が不正です:` prefix and argparse's wording, as in cli.py.
_ARGPARSE_JA: tuple[tuple[str, str], ...] = (
    (r"argument (?P<a>.+?): ignored explicit argument (?P<v>.+)", "{a} は値を取りません（指定値: {v}）"),
)


class _Parser(argparse.ArgumentParser):
    """argparse with Japanese help and exit 1 on bad arguments (same as cli.py)."""

    def format_help(self) -> str:  # noqa: D401 — argparse hook
        return USAGE

    def format_usage(self) -> str:
        return USAGE.splitlines()[0] + "\n"

    def error(self, message: str) -> None:  # type: ignore[override]
        for pattern, template in _ARGPARSE_JA:
            m = re.fullmatch(pattern, message)
            if m:
                message = template.format(**m.groupdict())
                break
        print(f"引数が不正です: {message}", file=sys.stderr)
        raise SystemExit(1)


def load_cases(path: Path) -> list[dict]:
    """Read cases.jsonl. Blank lines are skipped; any malformed line raises ValueError."""
    cases: list[dict] = []
    with path.open(encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, 1):
            line = raw.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"cases.jsonl の {lineno} 行目が JSON として読めません: {exc.msg}") from None
            if not isinstance(obj, dict) or any(k not in obj for k in REQUIRED):
                raise ValueError(
                    f"cases.jsonl の {lineno} 行目に必須キーがありません（{', '.join(REQUIRED)}）")
            if not all(isinstance(obj[k], str) for k in REQUIRED[:-1]):
                raise ValueError(f"cases.jsonl の {lineno} 行目: id / risk / kind / input は文字列です")
            if not isinstance(obj["expect"], list) or not all(isinstance(e, str) for e in obj["expect"]):
                raise ValueError(f"cases.jsonl の {lineno} 行目: expect は文字列の配列です")
            cases.append(obj)
    return cases


def main(argv: list[str] | None = None) -> int:
    for name in ("stdout", "stderr"):  # best effort: Japanese output on non-UTF-8 locales
        reconfigure = getattr(getattr(sys, name, None), "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass
    parser = _Parser(prog="evals/run.py", add_help=False)
    parser.add_argument("-h", "--help", action="help")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args, rest = parser.parse_known_args(argv)
    if rest:
        print(f"引数が不正です: 不明な引数 {' '.join(rest)}", file=sys.stderr)
        return 1
    if not args.dry_run:
        print("v1 は --dry-run のみ対応しています（BUILD_PLAN §3）", file=sys.stderr)
        return 1
    try:
        cases = load_cases(CASES_PATH)
    except FileNotFoundError:
        print(f"ケース一覧が見つかりません: {CASES_PATH}", file=sys.stderr)
        return 1
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(cases, ensure_ascii=False))
    else:
        for case in cases:
            print(f"{case['id']}\t{case['risk']}\t{case['kind']}\t{case['input']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
