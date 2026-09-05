#!/usr/bin/env python3
"""Explicit native CLI probe: update/rollback while old hook files remain readable.

All host configuration and state use temporary directories. No model is called.
"""
from pathlib import Path
import json
import hashlib
import os
import shlex
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from installer.hosts import _executable
from tests.test_installer import InstallerTests


def main() -> int:
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

        for version, fail in (("0.1.0-beta.2", False), ("0.1.0-beta.3", True)):
            source = fixture.base / version
            fixture._make_source(source, version)
            if fail:
                # Fail after both native managers have switched, during installed smoke.
                (source / "plugins/kiseki-da/scripts/hook_entry.py").write_text("raise SystemExit(13)\n")
                (source / "plugins/claude-code/kiseki-da/scripts/hook_entry.py").write_text("raise SystemExit(13)\n")
            env = dict(fixture.env, KISEKI_DA_MARKETPLACE_SOURCE=str(source))
            result = fixture.run_cli("update", "--yes", "--source", str(source), env=env)
            assert result.returncode == (2 if fail else 0), result.stderr + result.stdout
            if fail:
                assert "status: rolled_back" in result.stdout, result.stderr + result.stdout
            metadata = snapshot()
            assert metadata["version"] == "0.1.0-beta.2", metadata
            for cache, signature in tracked.items():
                actual = contents(cache)
                changed = [name for name in set(actual) | set(signature)
                           if actual.get(name) != signature.get(name)]
                assert not changed, f"Changed cache: {cache}: {changed}"
            print("native rollback PASS" if fail else "native update PASS", flush=True)
        stop.set()
        watcher.join()
        assert not missing, missing[:3]
        print("PASS: both hosts; old hooks continuously readable; plugin contents unchanged", flush=True)
        return 0
    finally:
        stop.set()
        if watcher is not None:
            watcher.join()
        fixture.tearDown()


if __name__ == "__main__":
    raise SystemExit(main())
