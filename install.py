#!/usr/bin/env python3
"""Kiseki DA bootstrap entry point.

The release ZIP and a Git clone intentionally use this same entry point.  The
installer itself has no third-party dependencies and supports Python 3.11-3.14.
"""
from __future__ import annotations

import sys
from pathlib import Path

# `--dry-run` promises zero writes, including no import-generated __pycache__
# beside an extracted release tree.
sys.dont_write_bytecode = True


def main() -> int:
    if not ((3, 11) <= sys.version_info[:2] <= (3, 14)):
        sys.stderr.write("Kiseki DA は Python 3.11〜3.14 が必要です。\n")
        return 1
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from installer.cli import main as installer_main

    return installer_main()


if __name__ == "__main__":
    raise SystemExit(main())
