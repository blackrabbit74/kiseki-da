#!/usr/bin/env python3
"""Exercise native Windows install, restart update, rollback and failure recovery.

Uses isolated host/state homes. Never modifies an existing installation or trust.
No model invocation. Requires installed Claude/Codex executables and two sources.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import sys
import tomllib
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from installer import operations
from installer.util import InstallerError


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--old-source", type=Path, required=True)
    parser.add_argument("--new-source", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--from-disabled", action="store_true")
    args = parser.parse_args()
    base = args.output.resolve()
    base.mkdir(parents=True, exist_ok=False)
    for host in ("codex", "claude"):
        (base / host).mkdir()
    home = base / "state"
    env = {"KISEKI_DA_HOME": str(home), "CODEX_HOME": str(base / "codex"),
           "CLAUDE_CONFIG_DIR": str(base / "claude"), "KISEKI_DA_SCRIPTS_DIR": str(base / "bin"),
           "KISEKI_DA_POINTER": str(base / "location"), "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1"}
    answers = {"identity": {"name": "試験利用者", "timezone": "Asia/Tokyo", "languages": ["ja"]}, "persona": {}}
    cases = []

    def record(name, code, result):
        (base / f"{name}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        print(f"{name}: code={code}, status={result.get('status')}, transaction={result.get('transaction')}", flush=True)

    def install(source, update=False):
        return operations.install(hosts=["claude-code", "codex"], scope="user", project=None,
                                  answers={} if update else answers, yes=True, dry_run=False,
                                  source=source.resolve(), update_mode=update, restart_update=update, local_source=True,
                                  enable_plugin=update and args.from_disabled)

    with patch.dict(os.environ, env):
        code, result = install(args.old_source)
        record("install-old", code, result)
        assert code == 0, result
        old_version = (args.old_source / "VERSION").read_text().strip()
        old_ownership = json.loads((home / "install.json").read_text(encoding="utf-8"))["host_ownership"]
        profile = hashlib.sha256((home / "profile.toml").read_bytes()).hexdigest()
        if args.from_disabled:
            config = base / "codex/config.toml"
            disabled, count = re.subn(r'(\[plugins\."kiseki-da@kiseki-da"\]\s*enabled\s*=\s*)true',
                                      r'\1false', config.read_text(encoding="utf-8"))
            assert count == 1
            config.write_text(disabled, encoding="utf-8")

        def validate_old():
            assert json.loads((home / "current.json").read_text())["version"] == old_version
            operations._smoke_installed_plugins(old_ownership, old_version)
            assert hashlib.sha256((home / "profile.toml").read_bytes()).hexdigest() == profile
            if args.from_disabled:
                config = tomllib.loads((base / "codex/config.toml").read_text(encoding="utf-8"))
                assert config["plugins"]["kiseki-da@kiseki-da"]["enabled"] is False

        code, result = install(args.new_source, True)
        record("update-new", code, result)
        assert code == 0 and result["restart_required"], result
        assert hashlib.sha256((home / "profile.toml").read_bytes()).hexdigest() == profile
        code, restored = operations.rollback(result["transaction"])
        record("rollback", code, restored)
        assert code == 0, restored
        validate_old()
        cases.append("native update and manual rollback preserve old runtime/profile")

        with patch.object(operations, "_smoke_installed_plugins", side_effect=InstallerError("injected post-install failure")):
            code, failed = install(args.new_source, True)
        record("failure-recovery", code, failed)
        assert code == 2 and failed["status"] == "rolled_back", failed
        validate_old()
        cases.append("failure after both native managers restores old runtime/profile")
        (base / "result.json").write_text(json.dumps({"passed": True, "cases": cases,
            "isolated": True, "production_modified": False, "hook_trust_modified": False}, ensure_ascii=False, indent=2), encoding="utf-8")
        print("PASS native Windows update, rollback and injected-failure recovery", flush=True)


if __name__ == "__main__":
    main()
