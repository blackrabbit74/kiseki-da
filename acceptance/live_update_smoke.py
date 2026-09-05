#!/usr/bin/env python3
"""Explicit native CLI probe: update/rollback while old hook files remain readable.

All host configuration and state use temporary directories. No model is called.
"""
from pathlib import Path
import json
import hashlib
import argparse
import os
import shlex
import sys
import subprocess
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from installer.hosts import _executable
from installer.operations import _smoke_installed_plugins
from tests.test_installer import InstallerTests


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--remote", action="store_true", help="公開済みGitタグbeta.4/beta.5で参照変更とrollbackを検証")
    args = parser.parse_args()
    fixture = InstallerTests()
    fixture.setUp()
    stop = threading.Event()
    watcher = None
    missing = []
    tracked = {}
    def contents(path):
        # Claude writes its own orphan timestamp when a version becomes inactive.
        return {str(p.relative_to(path)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in path.rglob("*") if p.is_file() and p != path / ".orphaned_at"}
    try:
        for host, variable in (("codex", "KISEKI_DA_CODEX_COMMAND"),
                               ("claude-code", "KISEKI_DA_CLAUDE_COMMAND")):
            fixture.env[variable] = shlex.join(_executable(host))
        Path(fixture.env["CODEX_HOME"]).mkdir(parents=True)
        fixture.env.pop("KISEKI_DA_MARKETPLACE_SOURCE", None)
        if args.remote:
            fixture.source = fixture.base / "remote-start"
            fixture._make_source(fixture.source, "0.1.0-beta.4")
        else:
            fixture.env["KISEKI_DA_MARKETPLACE_SOURCE"] = str(fixture.source)
        result = fixture.install("all")
        assert result.returncode == 0, result.stderr + result.stdout

        def snapshot():
            metadata = json.loads((fixture.home / "install.json").read_text())
            for host, item in metadata["host_ownership"].items():
                path = Path(item["installed_path"])
                tracked.setdefault(path, contents(path))
            return metadata

        snapshot()
        def watch():
            while not stop.is_set():
                for cache in tuple(tracked):
                    for suffix in ("scripts/hook_entry.py", "core/ctx/cli.py"):
                        try:
                            (cache / suffix).read_bytes()
                        except OSError as exc:
                            missing.append(str(exc))
                time.sleep(0.005)
        watcher = threading.Thread(target=watch)
        watcher.start()

        cases = (("0.1.0-beta.5", False), ("0.1.0-beta.4", True)) if args.remote else (
            ("0.1.0-beta.2", False), ("0.1.0-beta.3", True))
        expected_version = cases[0][0]
        for version, fail in cases:
            source = fixture.base / version
            fixture._make_source(source, version)
            if fail:
                # Fail after both native managers switch without corrupting any cached hook.
                operations = source / "installer/operations.py"
                needle = 'def _smoke_installed_plugins(host_ownership: dict[str, dict[str, Any]], version: str) -> None:\n'
                text = operations.read_text()
                assert needle in text
                operations.write_text(text.replace(needle, needle + '    raise InstallerError("native rollback probe")\n', 1))
            env = dict(fixture.env)
            if not args.remote:
                env["KISEKI_DA_MARKETPLACE_SOURCE"] = str(source)
            result = subprocess.run([sys.executable, str(source / "install.py"), "update", "--yes",
                                     "--source", str(source)], env=env, text=True, capture_output=True, timeout=180)
            assert result.returncode == (2 if fail else 0), result.stderr + result.stdout
            if fail:
                assert "status: rolled_back" in result.stdout, result.stderr + result.stdout
            metadata = snapshot()
            assert metadata["version"] == expected_version, metadata
            for host, variable in (("codex", "KISEKI_DA_CODEX_COMMAND"), ("claude-code", "KISEKI_DA_CLAUDE_COMMAND")):
                data = json.loads(subprocess.check_output([*shlex.split(env[variable]), "plugin", "list", "--json"], env=env, text=True))
                rows = data if isinstance(data, list) else data["installed"]
                entry = next(row for row in rows if "kiseki-da" in str(row.get("id", row.get("pluginId", ""))))
                assert entry["version"] == expected_version, (host, entry)
            for cache, signature in tracked.items():
                actual = contents(cache)
                changed = [name for name in set(actual) | set(signature)
                           if actual.get(name) != signature.get(name)]
                assert not changed, f"Changed cache: {cache}: {changed}"
            print("native rollback PASS" if fail else "native update PASS", flush=True)
        stop.set()
        watcher.join()
        assert not missing, missing[:3]
        for cache in tracked:
            host = "codex" if (cache / ".codex-plugin/plugin.json").is_file() else "claude-code"
            manifest = cache / (".codex-plugin" if host == "codex" else ".claude-plugin") / "plugin.json"
            version = json.loads(manifest.read_text())["version"]
            _smoke_installed_plugins({host: {"installed_path": str(cache)}}, version)
        print("PASS: both hosts; old hooks continuously readable and executable; plugin contents unchanged", flush=True)
        return 0
    finally:
        stop.set()
        if watcher is not None:
            watcher.join()
        fixture.tearDown()


if __name__ == "__main__":
    raise SystemExit(main())
