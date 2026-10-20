"""Hooks never start a process or open a network connection (repository rule in CLAUDE.md).

Every acceptance fixture runs through the real `cli.py hook` entry in-process while process and network entry
points are replaced by recorders. A modification that makes any hook call out fails here.
"""
from __future__ import annotations

import contextlib
import io
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "kiseki-da"
FIXTURES = ROOT / "acceptance" / "fixtures"
EVENTS = ("session-start", "pre-tool", "post-tool", "stop", "session-end")
HOSTS = {"cc": "claude-code", "codex": "codex"}


def fixture_runs() -> list[tuple[str, str, Path]]:
    runs = []
    for prefix, env in HOSTS.items():
        for event in EVENTS:
            for path in sorted(FIXTURES.glob(f"{prefix}-{event}*.json")):
                runs.append((event, env, path))
    return runs


class HookIsolationTest(unittest.TestCase):
    def test_hooks_make_no_process_or_network_calls(self):
        sys.path.insert(0, str(PLUGIN))
        try:
            from core.ctx import cli
        finally:
            sys.path.remove(str(PLUGIN))
        runs = fixture_runs()
        self.assertGreaterEqual(len(runs), 15)
        calls: list[str] = []

        def recorder(name):
            def record(*args, **kwargs):
                calls.append(name)
                raise AssertionError(f"hook called {name}")
            return record

        with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as workspace:
            (Path(workspace) / "repo").mkdir()
            with mock.patch.dict(os.environ, {"KISEKI_DA_HOME": home}), \
                    contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(cli.main(["init"]), 0)
            outputs = []
            patches = (
                mock.patch.object(subprocess, "run", recorder("subprocess.run")),
                mock.patch.object(subprocess, "Popen", recorder("subprocess.Popen")),
                mock.patch.object(os, "system", recorder("os.system")),
                mock.patch.object(socket, "create_connection", recorder("socket.create_connection")),
                mock.patch.object(socket.socket, "connect", recorder("socket.connect")),
                mock.patch.object(urllib.request, "urlopen", recorder("urllib.request.urlopen")),
            )
            with contextlib.ExitStack() as stack:
                for patch in patches:
                    stack.enter_context(patch)
                stack.enter_context(mock.patch.dict(os.environ, {"KISEKI_DA_HOME": home}))
                for event, env, path in runs:
                    # POSIX form: a Windows path's backslashes would be invalid escapes inside the JSON payload
                    payload = path.read_text(encoding="utf-8").replace("__FX__", FIXTURES.as_posix()) \
                        .replace("__CWD__", Path(workspace).as_posix())
                    out = io.StringIO()
                    with mock.patch.object(sys, "stdin", io.StringIO(payload)), contextlib.redirect_stdout(out), \
                            contextlib.redirect_stderr(io.StringIO()):
                        rc = cli.main(["hook", event, "--env", env])
                    self.assertEqual(rc, 0, path.name)
                    outputs.append(out.getvalue())
        self.assertEqual(calls, [])
        # The run is not degenerate: the guard fixtures produced decisions.
        self.assertTrue(any('"deny"' in text for text in outputs))


if __name__ == "__main__":
    unittest.main()
