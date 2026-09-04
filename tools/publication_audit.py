#!/usr/bin/env python3
"""Fail-closed audit for files that may enter a public Kiseki DA release."""
from __future__ import annotations

import hashlib
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "kiseki-da"
BANNED_NAMES = {".DS_Store", "HANDOFF.md", "HANDOFF.json", "BUILD_BRIEF.md", "PROMPT.md"}
BANNED_PARTS = {"build", "__pycache__", ".pytest_cache", "release", "dist"}
PRIVATE_PATTERNS = (
    re.compile(r"/Users/" + r"yoshitadaegawa(?:/|\b)"),
    re.compile(r"/private/" + r"tmp(?:/|\b)"),
    re.compile(r"\.codex/(?:sessions|archived_sessions)/"),
    re.compile(r"rollout-\d{4}-\d{2}-\d{2}"),
)
PRIVATE_IDENTITY_PATTERNS = (
    re.compile("Yoshitada" + r"\s+" + "Egawa"),
    re.compile("江川" + r"\s*" + "義匡"),
)
GENERIC_HOME_PATTERNS = (
    re.compile("/" + r"Users/([^/\s]+)(?:/|\b)"),
    re.compile("/" + r"home/([^/\s]+)(?:/|\b)"),
    re.compile(r"[A-Za-z]:\\" + r"Users\\([^\\\s]+)\\"),
)
GENERIC_HOME_EXAMPLES = {"demo", "example", "user", "username", "x", "<user>"}
HIGH_CONFIDENCE_SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{32,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----[\s\S]{40,}?"
               r"-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)
TEXT_SUFFIXES = {"", ".md", ".py", ".json", ".jsonl", ".toml", ".yml", ".yaml", ".sh", ".txt"}
RELEASE_GATES = (
    "user_publication_approval",
)


def tracked_files() -> list[Path]:
    proc = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True)
    return [ROOT / p.decode("utf-8") for p in proc.stdout.split(b"\0") if p]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=True,
    ).stdout.strip()


def _release_gates(
    path: Path | None, *, version: str, commit_sha: str, tree_sha256: str,
) -> tuple[bool, list[str]]:
    if path is None or not path.is_file():
        return False, list(RELEASE_GATES)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False, ["release_gates_invalid"]
    gates = data.get("gates") if isinstance(data, dict) else None
    if (not isinstance(data, dict) or data.get("schema") != 1 or data.get("version") != version
            or data.get("commit_sha") != commit_sha
            or data.get("tree_sha256") != tree_sha256 or not isinstance(gates, dict)):
        return False, ["release_gates_invalid"]
    missing = [name for name in RELEASE_GATES
               if not isinstance(gates.get(name), dict)
               or gates[name].get("passed") is not True
               or not isinstance(gates[name].get("evidence"), str)
               or not gates[name]["evidence"].strip()]
    return not missing, missing


def audit(gates_path: Path | None = None) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    files = tracked_files()
    for path in files:
        rel = path.relative_to(ROOT)
        if (rel.name in BANNED_NAMES or any(part in BANNED_PARTS for part in rel.parts)
                or rel.parts[:2] == ("docs", "background")):
            errors.append(f"公開対象外のpathがtrackedです: {rel}")
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern in PRIVATE_PATTERNS:
            if pattern.search(text):
                errors.append(f"private path/session marker: {rel}: {pattern.pattern}")
        if "[TO" + "DO" in text or "TO" + "DO:" in text:
            errors.append(f"未解決placeholder: {rel}")
        if rel.as_posix() != "LICENSE":
            for pattern in PRIVATE_IDENTITY_PATTERNS:
                if pattern.search(text):
                    errors.append(f"LICENSE外のprivate author identity: {rel}")
        for pattern in GENERIC_HOME_PATTERNS:
            for match in pattern.finditer(text):
                if match.group(1).casefold() not in GENERIC_HOME_EXAMPLES:
                    errors.append(f"local user home path: {rel}")
                    break
        for pattern in HIGH_CONFIDENCE_SECRET_PATTERNS:
            if pattern.search(text):
                errors.append(f"high-confidence secret pattern: {rel}")

    version_path = ROOT / "VERSION"
    if not version_path.is_file():
        errors.append("VERSIONがありません")
        version = ""
    else:
        version = version_path.read_text(encoding="utf-8").strip()
    manifests = [
        PLUGIN / ".codex-plugin" / "plugin.json",
        PLUGIN / ".claude-plugin" / "plugin.json",
        ROOT / ".claude-plugin" / "marketplace.json",
    ]
    for path in manifests:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            errors.append(f"manifestを読めません: {path.relative_to(ROOT)}: {exc}")
            continue
        if data.get("version") != version:
            errors.append(f"version不一致: {path.relative_to(ROOT)}: {data.get('version')} != {version}")

    tree_sha256 = hashlib.sha256(
        "\n".join(f"{sha256(p)}  {p.relative_to(ROOT).as_posix()}" for p in files if p.is_file()).encode()
    ).hexdigest()
    commit_sha = _git_commit()
    release_ready, blockers = _release_gates(
        gates_path, version=version, commit_sha=commit_sha, tree_sha256=tree_sha256,
    )
    result = {
        "ok": not errors,
        "release_ready": not errors and release_ready,
        "release_blockers": blockers,
        "tracked_files": len(files),
        "runtime_files": sum(1 for p in files if PLUGIN in p.parents),
        "version": version,
        "commit_sha": commit_sha,
        "errors": errors,
        "warnings": warnings,
        "tree_sha256": tree_sha256,
    }
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gates", type=Path)
    parser.add_argument("--require-release-ready", action="store_true")
    args = parser.parse_args(argv)
    result = audit(args.gates)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] and (result["release_ready"] or not args.require_release_ready) else 1


if __name__ == "__main__":
    raise SystemExit(main())
