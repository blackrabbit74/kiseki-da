#!/usr/bin/env python3
"""Windows maintenance probe: real commands, synthetic hook transport, no model calls.

All writes stay in the requested diagnostics directory. Installed state is read
only when --profile is supplied; native managers use fresh host homes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from installer.operations import _runtime_source, _write_launchers
from installer.transaction import Transaction


def quote(value):
    return "'" + str(value).replace("'", "''") + "'"


def run(argv, env, cwd, payload=None, timeout=60):
    return subprocess.run(list(map(str, argv)), cwd=cwd, env=env,
                          input=json.dumps(payload) if payload is not None else "",
                          capture_output=True, text=True, encoding="utf-8", errors="replace",
                          timeout=timeout, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)


def check(result):
    if result.returncode:
        raise AssertionError(f"command exit {result.returncode}: {result.stderr[-1000:]}")
    return result.stdout


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--profile", type=Path)
    parser.add_argument("--native", action="store_true")
    args = parser.parse_args()
    base = args.output.resolve()
    base.mkdir(parents=True, exist_ok=False)
    powershell = shutil.which("pwsh") or shutil.which("powershell.exe")
    if not powershell:
        raise SystemExit("PowerShellが必要です")
    records = []
    for host in ("codex", "claude-code"):
        case = base / host
        work = case / "workspace"
        work.mkdir(parents=True)
        home = case / "state"
        runtime = home / "runtime" / (ROOT / "VERSION").read_text().strip()
        _runtime_source(ROOT, runtime)
        env = dict(os.environ, KISEKI_DA_HOME=str(home), PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1",
                   KISEKI_DA_SCRIPTS_DIR=str(case / "public-bin"))
        previous_scripts = os.environ.get("KISEKI_DA_SCRIPTS_DIR")
        os.environ["KISEKI_DA_SCRIPTS_DIR"] = env["KISEKI_DA_SCRIPTS_DIR"]
        try:
            tx = Transaction(home, "maintenance-probe")
            launchers, _ = _write_launchers(tx, home, runtime, {})
            tx.write_json(home / "current.json", {"runtime": str(runtime), "version": runtime.name})
            tx.write_json(home / "install.json", {"management_launchers": [
                {"path": str(p.resolve()), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in launchers]})
            tx.commit()
        finally:
            if previous_scripts is None:
                os.environ.pop("KISEKI_DA_SCRIPTS_DIR", None)
            else:
                os.environ["KISEKI_DA_SCRIPTS_DIR"] = previous_scripts
        plugin = runtime / ("plugins/kiseki-da" if host == "codex" else "plugins/claude-code/kiseki-da")
        cli = plugin / "core/ctx/cli.py"
        wrapper = plugin / "scripts/hook_entry.py"
        env["PATH"] = str(home / "bin") + os.pathsep + env.get("PATH", "")
        env["PLUGIN_ROOT"] = env["CLAUDE_PLUGIN_ROOT"] = str(plugin)
        check(run([sys.executable, cli, "init"], env, work))
        if args.profile:
            shutil.copyfile(args.profile, home / "profile.toml")
        profile_hash = hashlib.sha256((home / "profile.toml").read_bytes()).hexdigest()
        sid = "maintenance-probe-" + host

        def hook(event, name, **fields):
            payload = {"session_id": sid, "cwd": str(work), "hook_event_name": name, **fields}
            return check(run([sys.executable, wrapper, event, host], env, work, payload))

        count = 0
        def execute(command, *, expected=0, denied=False):
            nonlocal count
            count += 1
            fields = {"tool_name": "PowerShell", "tool_input": {"command": command},
                      "tool_use_id": f"real-powershell-{count}"}
            before = hook("pre-tool", "PreToolUse", **fields)
            decision = json.loads(before).get("hookSpecificOutput", {}).get("permissionDecision") if before else None
            if denied:
                assert decision == "deny", before
                return ""
            assert decision is None, before
            result = run([powershell, "-NoProfile", "-NonInteractive", "-Command", command], env, work)
            assert result.returncode == expected, result.stderr
            hook("post-tool", "PostToolUse", **fields,
                 tool_response={"exit_code": result.returncode, "stdout": result.stdout})
            return result.stdout

        resident = hook("session-start", "SessionStart", source="startup")
        fixed = "& " + quote(sys.executable) + " -B " + quote(cli)
        launcher = "kiseki-da"
        suffix = " --sid " + sid
        execute(launcher + " task new --id repair --risk R1 --goal '保守試験'" + suffix)
        execute(launcher + " task set repair --constraint " + quote("利用者指示を保持する。" * 420) + suffix)
        (work / "README.md").write_text("release deploy\n", encoding="utf-8")
        execute("Get-Content README.md")
        if shutil.which("rg"):
            execute('rg -n "release|deploy" README.md')
        execute("Set-Content result.txt changed", denied=True)
        first = execute(fixed + " context required --json" + suffix)
        required = json.loads(first)
        for page in range(2, required["pages"] + 1):
            execute(launcher + f" context required --page {page}" + suffix)
        execute("Set-Content result.txt changed")
        execute(launcher + " task set repair --add-criterion '結果を読み返す :: Get-Content result.txt'" + suffix)
        execute(launcher + " task close repair" + suffix, expected=1)
        execute("Get-Content result.txt")
        execute(launcher + " task set repair --evidence C1=last" + suffix)
        execute(launcher + " task close repair" + suffix)
        execute(launcher + " task new --id pending --risk R1 --goal '未検証を保存する'" + suffix)
        execute(launcher + " task set pending --constraint '追加条件を保持する'" + suffix)
        execute(fixed + " task defer pending --reason '実アプリの連続対話は未検証'" + suffix)
        stopped = hook("stop", "Stop")
        hook("session-end", "SessionEnd", reason="probe-complete")
        assert not stopped
        assert hashlib.sha256((home / "profile.toml").read_bytes()).hexdigest() == profile_hash
        records.append({"host": host, "real_powershell_commands": count - 1,
                        "constraint_pages": required["pages"], "close_and_defer": True,
                        "profile_preserved": True, "lapis_loaded": "ラピス" in resident,
                        "hook_transport": "synthetic payloads with actual subprocess outputs"})
        print(json.dumps(records[-1], ensure_ascii=False), flush=True)
        if args.native and host == "claude-code":
            native_home = case / "native-claude"
            native_home.mkdir()
            (native_home / "settings.json").write_text(json.dumps({"pluginConfigs": {
                "kiseki-da@inline": {"options": {"python_executable": sys.executable}}}}), encoding="utf-8")
            native_env = dict(env, CLAUDE_CONFIG_DIR=str(native_home))
            debug = case / "native-startup.log"
            result = run([shutil.which("claude"), "--init-only", "--plugin-dir", plugin,
                          "--debug-file", debug], native_env, work, timeout=60)
            check(result)
            log = debug.read_text(encoding="utf-8", errors="replace")
            assert "対話方針（Kiseki DA）" in log
            records[-1]["native_init_only"] = True
        if args.native and host == "codex":
            from installer.hosts import HostManager
            native_home = case / "native-codex"
            cached = HostManager("codex").stage_codex_plugin(runtime, native_home, runtime.name)
            assert (cached / "core/ctx/evidence.py").read_bytes() == (cli.parent / "evidence.py").read_bytes()
            records[-1]["native_plugin_manager"] = True
    report = {"cases": records, "production_modified": False, "real_app_conversation": "not tested"}
    (base / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("PASS: Windows management flow; installed environment unchanged.", flush=True)


if __name__ == "__main__":
    main()
