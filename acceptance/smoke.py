#!/usr/bin/env python3
"""Cross-platform, LLM-free Kiseki DA acceptance smoke."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "plugins" / "kiseki-da" / "core" / "ctx" / "cli.py"


def run(args: list[str], env: dict[str, str], payload: dict | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(CLI), *args], input=json.dumps(payload) if payload else None,
                          text=True, encoding="utf-8", errors="replace", capture_output=True, env=env)


def require(condition: bool, label: str, detail: str = "") -> None:
    if not condition:
        raise AssertionError(f"{label}: {detail}")
    print(f"PASS {label}")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="kiseki-da-state-") as state, tempfile.TemporaryDirectory(
            prefix="kiseki-da-work-") as workspace:
        env = os.environ.copy()
        env["KISEKI_DA_HOME"] = state
        env.pop("PA_HOME", None)
        require(run(["init"], env).returncode == 0, "init")
        start_payload = {"session_id": "smoke", "hook_event_name": "SessionStart", "cwd": workspace,
                         "source": "startup"}
        started = run(["hook", "session-start", "--env", "claude-code"], env, start_payload)
        require(started.returncode == 0 and "Kiseki DA" in started.stdout and "session: smoke" in started.stdout,
                "SessionStart", started.stderr or started.stdout)
        require(run(["task", "new", "--goal", "cross-platform smoke", "--risk", "R1", "--id", "smoke"], env).returncode == 0,
                "task new")
        require(run(["task", "set", "smoke", "--add-criterion", "テストが成功する :: pytest -q"], env).returncode == 0,
                "criterion")
        require(run(["task", "close", "smoke"], env).returncode == 1, "close rejects missing evidence")
        post_payload = {"session_id": "smoke", "hook_event_name": "PostToolUse", "cwd": workspace,
                        "tool_name": "Bash", "tool_use_id": "smoke-pytest", "tool_input": {"command": "pytest -q"},
                        "tool_response": {"stdout": "1 passed", "exit_code": 0}}
        require(run(["hook", "post-tool", "--env", "claude-code"], env, post_payload).returncode == 0,
                "PostToolUse")
        require(run(["task", "set", "smoke", "--evidence", "C1=last"], env).returncode == 0, "evidence")
        require(run(["task", "close", "smoke"], env).returncode == 0, "close with evidence")
        win_payload = {"session_id": "smoke", "hook_event_name": "PreToolUse", "cwd": workspace,
                       "tool_name": "PowerShell",
                       "tool_input": {"command": r"Remove-Item C:\work\old -Recurse -Force"}}
        guarded = run(["hook", "pre-tool", "--env", "claude-code"], env, win_payload)
        require('"deny"' in guarded.stdout, "Windows destructive guard", guarded.stdout)
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
