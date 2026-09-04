"""Installer constants shared by source and installed launchers."""
from __future__ import annotations

from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = SOURCE_ROOT / "VERSION"
VERSION = VERSION_FILE.read_text(encoding="utf-8").strip()
TAG = f"v{VERSION}"
PRODUCT = "Kiseki DA"
PLUGIN_ID = "kiseki-da"
MARKETPLACE_ID = "kiseki-da"
MARKETPLACE_REPO = "blackrabbit74/kiseki-da"
HOSTS = ("claude-code", "codex")
MIN_VERSIONS = {"claude-code": (2, 1, 142), "codex": (0, 151, 0)}

RUNTIME_EXCLUDES = {
    ".DS_Store",
    ".git",
    ".pytest_cache",
    "__pycache__",
}
