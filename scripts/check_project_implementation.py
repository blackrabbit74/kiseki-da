#!/usr/bin/env python3
"""Run the repository's relevant suites without changing installed hosts."""
from pathlib import Path
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CHECKS = [
    ["-m", "unittest", "discover", "-s", "tests", "-t", "."],
    ["-m", "unittest", "discover", "-s", "plugins/kiseki-da/core/tests", "-t", "plugins/kiseki-da"],
    ["acceptance/smoke.py"],
]

if __name__ == "__main__":
    os.environ["PYTHONUTF8"] = "1"
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    # Use the available desktop host for the model-free native probes. Tests
    # still run on other systems, reporting their native checks as skipped.
    if "KISEKI_DA_NATIVE_CODEX" not in os.environ:
        for app in ("ChatGPT.app", "Codex.app"):
            candidate = Path("/Applications") / app / "Contents/Resources/codex"
            if candidate.is_file() and os.access(candidate, os.X_OK):
                os.environ["KISEKI_DA_NATIVE_CODEX"] = str(candidate)
                break
    for args in CHECKS:
        result = subprocess.run([sys.executable, "-B", *args], cwd=ROOT, check=False)
        if result.returncode:
            raise SystemExit(result.returncode)
