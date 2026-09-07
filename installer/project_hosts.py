"""Generate host-local entry points for an independent Kiseki workspace.

These helpers return files for a new destination. They never edit installed
plugins, user configuration, or host trust records.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
EVENTS = {
    "SessionStart": "session-start",
    "UserPromptSubmit": "user-input",
    "PreToolUse": "pre-tool",
    "PostToolUse": "post-tool",
    "PostToolUseFailure": "post-tool",
    "Stop": "stop",
    "SessionEnd": "session-end",
}


def _hooks(entry: Path, host: str) -> dict:
    if host == "codex":
        template = ROOT / "plugins/kiseki-da/hooks/hooks.json"
    else:
        template = ROOT / "plugins/claude-code/kiseki-da/hooks/claude-code.json"
    hooks = copy.deepcopy(json.loads(template.read_text(encoding="utf-8"))["hooks"])
    python = str(Path(sys.executable).resolve())
    for event, groups in hooks.items():
        normalized = EVENTS[event]
        argv = [python, str(entry), "--hook", normalized, host]
        for group in groups:
            for handler in group["hooks"]:
                handler["command"] = shlex.join(argv)
                handler.pop("args", None)
                if host == "codex":
                    handler["commandWindows"] = subprocess.list2cmdline(argv)
                else:
                    handler.pop("commandWindows", None)
    return hooks


def host_files(destination: Path, entry: Path, skill_names: list[str], role: str = "child") -> dict[str, str]:
    """Return new project-local host files; review/trust stays with each host.

    Both hosts merge global and project hooks. Disabling the parent plugin only
    in this new project prevents the same events reaching two Kiseki states.
    No other plugin, hook, permission, or user skill setting is changed.
    """
    destination = destination.expanduser().resolve()
    entry = entry.expanduser().resolve()
    if not entry.is_relative_to(destination):
        raise ValueError("The Kiseki entry must be inside its destination workspace.")
    if role not in {"child", "main"}:
        raise ValueError("role must be child or main")
    if any(not isinstance(name, str) or not name for name in skill_names):
        raise ValueError("skill_names must contain nonempty names")
    codex = {
        "description": "Kiseki DA workspace hooks. Review and trust these definitions before use.",
        "hooks": _hooks(entry, "codex"),
    }
    claude = {
        "enabledPlugins": {"kiseki-da@kiseki-da": False},
        "hooks": _hooks(entry, "claude-code"),
    }
    return {
        ".codex/hooks.json": json.dumps(codex, ensure_ascii=False, indent=2) + "\n",
        ".codex/config.toml": (
            "# Local hooks use the fixed runtime in this workspace.\n"
            "# Existing user configuration and hook trust are preserved.\n"
            "[plugins.\"kiseki-da@kiseki-da\"]\n"
            "enabled = false\n\n"
            "[features]\n"
            "hooks = true\n"
        ),
        ".claude/settings.local.json": json.dumps(claude, ensure_ascii=False, indent=2) + "\n",
    }


def _tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in {"__pycache__", ".git"} for part in relative.parts) or path.suffix == ".pyc":
            continue
        if path.is_file():
            digest.update(str(relative).encode("utf-8"))
            digest.update(b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
    return digest.hexdigest()


def visibility_warnings(source: Path, destination: Path) -> list[str]:
    """Report exact personal skill copies that may remain visible to a host.

    Matching a skill's name alone is insufficient. This function is read-only;
    personal skill migration is a separate operation with explicit ownership.
    """
    source = source.expanduser().resolve()
    destination = destination.expanduser().resolve()
    skill_root = source / "skills" if (source / "skills").is_dir() else source
    originals = {
        skill.parent.name: skill.parent
        for skill in skill_root.rglob("SKILL.md")
        if skill.parent != skill_root
    }
    warnings: list[str] = []
    for host_folder in (".codex", ".agents", ".claude"):
        personal = Path.home() / host_folder / "skills"
        if not personal.is_dir():
            continue
        for name, original in sorted(originals.items()):
            candidate = personal / name
            if not (candidate / "SKILL.md").is_file() or candidate.resolve().is_relative_to(destination):
                continue
            try:
                same = _tree_hash(candidate) == _tree_hash(original)
            except OSError:
                same = False
            if same:
                warnings.append(f"Personal skill remains discoverable: {candidate} (exact copy of {original})")
    return warnings
