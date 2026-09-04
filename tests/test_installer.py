from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
INSTALL = ROOT / "install.py"


FAKE_MANAGER = r'''#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

host = sys.argv[1]
args = sys.argv[2:]
state_path = Path(os.environ["FAKE_MANAGER_STATE"])
try:
    state = json.loads(state_path.read_text(encoding="utf-8"))
except (OSError, ValueError):
    state = {}
record = state.setdefault(host, {"marketplace": False, "plugin": False})

inventory_failure = os.environ.get("FAKE_FAIL_INVENTORY")
if inventory_failure and inventory_failure in " ".join(args):
    print("injected inventory failure", file=sys.stderr)
    raise SystemExit(9)

if args == ["--version"]:
    print("9.9.9")
    raise SystemExit(0)
if args == ["plugin", "--help"]:
    print("marketplace install add remove")
    raise SystemExit(0)
if args[:4] == ["plugin", "marketplace", "list", "--json"]:
    print(json.dumps({"marketplaces": [{"name": "kiseki-da", "marketplaceSource": {
        "sourceType": "local" if record.get("marketplace_source", "").startswith("/") else "git",
        "source": record.get("marketplace_source", "https://github.com/blackrabbit74/kiseki-da.git"),
        "ref": record.get("marketplace_ref", "v0.1.0-beta.1")}}]
                      if record["marketplace"] else []}))
    raise SystemExit(0)
if args[:3] == ["plugin", "list", "--json"]:
    plugin_path = os.environ.get("FAKE_PLUGIN_PATH")
    installed = {"pluginId": "kiseki-da@kiseki-da", "name": "kiseki-da",
                 "marketplaceName": "kiseki-da", "installed": True, "enabled": True}
    if record.get("version"):
        installed["version"] = record["version"]
    if plugin_path:
        installed["source"] = {"source": "local", "path": plugin_path}
    print(json.dumps({"installed": [installed]
                      if record["plugin"] else [],
                      "available": [{"name": "kiseki-da", "description": "not installed"}]}))
    raise SystemExit(0)

joined = " ".join(args)
log_path = os.environ.get("FAKE_MANAGER_LOG")
if log_path:
    with open(log_path, "a", encoding="utf-8") as stream:
        stream.write(host + " " + joined + "\n")
fail_on = os.environ.get("FAKE_FAIL_ON")
if fail_on and fail_on in host + " " + joined:
    print("injected failure", file=sys.stderr)
    raise SystemExit(9)

if args[:3] == ["plugin", "marketplace", "add"]:
    record["marketplace"] = True
    record["marketplace_source"] = args[3]
    if "--ref" in args:
        record["version"] = args[args.index("--ref") + 1].removeprefix("v")
        record["marketplace_ref"] = args[args.index("--ref") + 1]
    elif len(args) > 3 and "@v" in args[3]:
        record["version"] = args[3].rsplit("@v", 1)[1]
    elif len(args) > 3 and "#v" in args[3]:
        record["version"] = args[3].rsplit("#v", 1)[1]
        record["marketplace_ref"] = "v" + record["version"]
elif args[:3] == ["plugin", "marketplace", "remove"]:
    record["marketplace"] = False
    record["plugin"] = False
elif len(args) >= 2 and args[:2] in (["plugin", "install"], ["plugin", "add"]):
    if not record["marketplace"]:
        print("marketplace missing", file=sys.stderr)
        raise SystemExit(8)
    record["plugin"] = True
elif len(args) >= 2 and args[:2] in (["plugin", "uninstall"], ["plugin", "remove"]):
    record["plugin"] = False
elif args[:3] in (["plugin", "marketplace", "update"], ["plugin", "marketplace", "upgrade"]):
    pass
else:
    print("unknown fake command: " + joined, file=sys.stderr)
    raise SystemExit(7)

if host == "claude-code" and args[:3] in (["plugin", "marketplace", "add"],
                                           ["plugin", "marketplace", "remove"]):
    settings = Path(os.environ["CLAUDE_CONFIG_DIR"]) / "settings.json"
    try:
        data = json.loads(settings.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    extra = data.setdefault("extraKnownMarketplaces", {})
    if args[2] == "add":
        extra["kiseki-da"] = {"source": {"source": "url", "url": record["marketplace_source"],
                                             "ref": record.get("marketplace_ref", "v0.1.0-beta.1")}}
    else:
        extra.pop("kiseki-da", None)
        if not extra:
            data.pop("extraKnownMarketplaces", None)
    settings.parent.mkdir(parents=True, exist_ok=True)
    settings.write_text(json.dumps(data, sort_keys=True) + "\n", encoding="utf-8")

settings_path = os.environ.get("FAKE_CLAUDE_SETTINGS") if host == "claude-code" else None
if settings_path and len(args) >= 2 and args[0] == "plugin" and args[1] in {"install", "uninstall"}:
    settings = Path(settings_path)
    try:
        data = json.loads(settings.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    plugins = data.setdefault("fakeNativePlugins", {})
    if args[1] == "install":
        plugins["kiseki-da"] = True
    else:
        plugins.pop("kiseki-da", None)
        if not plugins:
            data.pop("fakeNativePlugins", None)
    settings.parent.mkdir(parents=True, exist_ok=True)
    settings.write_text(json.dumps(data, sort_keys=True) + "\n", encoding="utf-8")

state_path.parent.mkdir(parents=True, exist_ok=True)
state_path.write_text(json.dumps(state), encoding="utf-8")
if len(args) >= 2 and args[:2] in (["plugin", "install"], ["plugin", "add"]):
    plugin_path = os.environ.get("FAKE_PLUGIN_PATH")
    if plugin_path:
        print(json.dumps({"installedPath": plugin_path}))
'''


class InstallerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.home = self.base / "状態 space 日本語"
        self.fake = self.base / "fake manager.py"
        self.fake.write_text(FAKE_MANAGER, encoding="utf-8")
        self.state = self.base / "manager-state.json"
        self.log = self.base / "manager.log"
        self.source = self.base / "source"
        self._make_source(self.source, "0.1.0-beta.1")
        self.empty_answers = self.base / "empty-answers.json"
        self.empty_answers.write_text(json.dumps({
            "identity": {"name": "", "timezone": "Asia/Tokyo", "languages": ["ja"]},
            "persona": {},
        }), encoding="utf-8")
        self.env = os.environ.copy()
        self.env.update({
            "KISEKI_DA_HOME": str(self.home),
            "KISEKI_DA_CLAUDE_COMMAND": f'{sys.executable} "{self.fake}" claude-code',
            "KISEKI_DA_CODEX_COMMAND": f'{sys.executable} "{self.fake}" codex',
            "FAKE_MANAGER_STATE": str(self.state),
            "FAKE_MANAGER_LOG": str(self.log),
            "CLAUDE_CONFIG_DIR": str(self.base / "claude-config"),
            "CODEX_HOME": str(self.base / "codex-config"),
            "KISEKI_DA_SCRIPTS_DIR": str(self.base / "user-scripts"),
            "KISEKI_DA_POINTER": str(self.base / "kiseki-da-location"),
            "FAKE_PLUGIN_PATH": str(self.source / "plugins" / "kiseki-da"),
            "PYTHONDONTWRITEBYTECODE": "1",
        })
        self.env.pop("FAKE_FAIL_ON", None)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _make_source(self, target: Path, version: str) -> None:
        target.mkdir(parents=True)
        shutil.copy2(ROOT / "install.py", target / "install.py")
        (target / "VERSION").write_text(version + "\n", encoding="utf-8")
        shutil.copytree(ROOT / "installer", target / "installer", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        shutil.copytree(ROOT / "plugins", target / "plugins", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        shutil.copytree(ROOT / ".claude-plugin", target / ".claude-plugin")
        shutil.copytree(ROOT / ".agents", target / ".agents")
        version_paths = (
            target / ".claude-plugin" / "marketplace.json",
            target / "plugins" / "kiseki-da" / ".claude-plugin" / "plugin.json",
            target / "plugins" / "kiseki-da" / ".codex-plugin" / "plugin.json",
        )
        for manifest in version_paths:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            data["version"] = version
            if manifest.name == "marketplace.json":
                for plugin in data.get("plugins", []):
                    if isinstance(plugin, dict) and plugin.get("name") == "kiseki-da":
                        plugin["version"] = version
            manifest.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def run_cli(self, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(INSTALL), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env or self.env,
            check=False,
        )

    def install(self, host: str = "all") -> subprocess.CompletedProcess[str]:
        return self.run_cli("install", "--host", host, "--scope", "user", "--answers", str(self.empty_answers),
                            "--yes", "--source", str(self.source))

    def manager_state(self) -> dict:
        return json.loads(self.state.read_text(encoding="utf-8")) if self.state.exists() else {}

    def mutation_log(self) -> list[str]:
        return self.log.read_text(encoding="utf-8").splitlines() if self.log.exists() else []

    def test_new_install_both_hosts_and_launcher_dispatch(self) -> None:
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        current = json.loads((self.home / "current.json").read_text(encoding="utf-8"))
        self.assertEqual(current["version"], "0.1.0-beta.1")
        self.assertIn("状態 space 日本語", current["runtime"])
        metadata = json.loads((self.home / "install.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["hosts"], ["claude-code", "codex"])
        self.assertEqual(metadata["security_settings"], "preserve")
        self.assertTrue(metadata["host_ownership"]["claude-code"]["marketplace_fingerprint"])
        self.assertTrue(metadata["host_ownership"]["codex"]["marketplace_fingerprint"])
        pointer = Path(self.env["KISEKI_DA_POINTER"])
        self.assertEqual(pointer.read_text(encoding="utf-8"), str(self.home.resolve()) + "\n")
        self.assertTrue(metadata["location_pointer"]["owned"])
        self.assertTrue((self.home / "bin" / "kiseki-da").is_file())
        self.assertTrue((self.home / "bin" / "kiseki-da.cmd").is_file())
        public_launcher = self.base / "user-scripts" / ("kiseki-da.cmd" if os.name == "nt" else "kiseki-da")
        self.assertTrue(public_launcher.is_file())
        state = self.manager_state()
        self.assertTrue(state["claude-code"]["plugin"])
        self.assertTrue(state["codex"]["plugin"])
        version = subprocess.run(
            [sys.executable, str(self.home / "bin" / "kiseki-da.py"), "version"],
            capture_output=True, text=True, env=self.env, check=False,
        )
        self.assertEqual(version.returncode, 0, version.stderr)
        self.assertEqual(version.stdout.strip(), "0.1.0-beta.1")
        if os.name != "nt":
            public_version = subprocess.run([str(public_launcher), "version"], capture_output=True, text=True,
                                            env=self.env, check=False)
            self.assertEqual((public_version.returncode, public_version.stdout.strip()), (0, "0.1.0-beta.1"))

    def test_dry_run_makes_no_state_writes_or_manager_mutations(self) -> None:
        result = self.run_cli("install", "--host", "all", "--scope", "user", "--yes", "--dry-run", "--source", str(self.source))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.home.exists())
        self.assertFalse(self.state.exists())
        self.assertFalse(self.log.exists())
        self.assertFalse(Path(self.env["KISEKI_DA_POINTER"]).exists())

    def test_claude_marketplace_remove_and_undo_are_user_scoped(self) -> None:
        sys.path.insert(0, str(ROOT))
        from installer.hosts import HostManager

        old_env = os.environ.copy()
        os.environ.update(self.env)
        try:
            manager = HostManager("claude-code")
            add, add_undo = manager.marketplace_add(version="0.1.0-beta.1")
            remove, remove_undo = manager.marketplace_remove(old_version="0.1.0-beta.1")
        finally:
            os.environ.clear()
            os.environ.update(old_env)
        self.assertEqual(add[-2:], ["--scope", "user"])
        self.assertEqual(add_undo[-2:], ["--scope", "user"])
        self.assertEqual(remove[-2:], ["--scope", "user"])
        self.assertEqual(remove_undo[-2:], ["--scope", "user"])

    @unittest.skipIf(os.name == "nt", "non-Windows Codex preflight")
    def test_codex_preflight_rejects_python3_below_311(self) -> None:
        sys.path.insert(0, str(ROOT))
        from installer.hosts import HostManager
        from installer.util import InstallerError

        def fake_which(name):
            return "/fake/codex" if name == "codex" else "/fake/python3"

        def fake_run(argv):
            if argv[0] == "/fake/python3":
                return subprocess.CompletedProcess(argv, 0, "3.10.14\n", "")
            return subprocess.CompletedProcess(argv, 0, "codex-cli 9.9.9\n", "")

        with mock.patch("installer.hosts.shutil.which", side_effect=fake_which), \
                mock.patch("installer.hosts.run_command", side_effect=fake_run):
            with self.assertRaisesRegex(InstallerError, "Python 3.11"):
                HostManager("codex").preflight()

    @unittest.skipIf(os.name == "nt", "non-Windows Codex preflight")
    def test_codex_preflight_rejects_python3_above_314(self) -> None:
        sys.path.insert(0, str(ROOT))
        from installer.hosts import HostManager
        from installer.util import InstallerError

        def fake_which(name):
            return "/fake/codex" if name == "codex" else "/fake/python3"

        def fake_run(argv):
            if argv[0] == "/fake/python3":
                return subprocess.CompletedProcess(argv, 0, "3.15.0\n", "")
            return subprocess.CompletedProcess(argv, 0, "codex-cli 9.9.9\n", "")

        with mock.patch("installer.hosts.shutil.which", side_effect=fake_which), \
                mock.patch("installer.hosts.run_command", side_effect=fake_run):
            with self.assertRaisesRegex(InstallerError, "3.11〜3.14"):
                HostManager("codex").preflight()

    def test_local_marketplace_override_is_not_given_git_ref(self) -> None:
        sys.path.insert(0, str(ROOT))
        from installer.hosts import HostManager
        with mock.patch.dict(os.environ, {
            "KISEKI_DA_CODEX_COMMAND": f'{sys.executable} "{self.fake}" codex',
            "KISEKI_DA_MARKETPLACE_SOURCE": str(ROOT),
        }):
            command, _ = HostManager("codex").marketplace_add(version="0.1.0-beta.1")
        self.assertNotIn("--ref", command)

    def test_public_marketplace_commands_use_explicit_https_and_tag(self) -> None:
        sys.path.insert(0, str(ROOT))
        from installer.hosts import HostManager
        old_env = os.environ.copy()
        os.environ.update(self.env)
        os.environ.pop("KISEKI_DA_MARKETPLACE_SOURCE", None)
        try:
            claude, _ = HostManager("claude-code").marketplace_add(version="0.1.0-beta.1")
            codex, _ = HostManager("codex").marketplace_add(version="0.1.0-beta.1")
        finally:
            os.environ.clear()
            os.environ.update(old_env)
        self.assertIn("https://github.com/blackrabbit74/kiseki-da.git#v0.1.0-beta.1", claude)
        self.assertIn("https://github.com/blackrabbit74/kiseki-da.git", codex)
        self.assertEqual(codex[codex.index("--ref") + 1], "v0.1.0-beta.1")

    def test_wsl_rejects_windows_host_cli_interop(self) -> None:
        sys.path.insert(0, str(ROOT))
        from installer.hosts import HostManager
        from installer.util import InstallerError
        with mock.patch.dict(os.environ, {"KISEKI_DA_CODEX_COMMAND": "codex", "WSL_DISTRO_NAME": "Ubuntu"}), \
                mock.patch("installer.hosts.shutil.which", return_value="/mnt/c/Program Files/Codex/codex.exe"):
            with self.assertRaises(InstallerError):
                HostManager("codex").preflight()

    def test_wsl_rejects_state_on_mounted_windows_drive(self) -> None:
        env = dict(self.env)
        env["WSL_DISTRO_NAME"] = "Ubuntu"
        env["KISEKI_DA_HOME"] = "/mnt/c/Users/demo/.kiseki-da"
        result = self.run_cli("install", "--host", "codex", "--scope", "user", "--dry-run",
                              "--source", str(self.source), env=env)
        self.assertEqual(result.returncode, 1)
        self.assertIn("/mnt/<drive>", result.stderr)

    def test_windows_acl_probe_is_fail_closed(self) -> None:
        sys.path.insert(0, str(ROOT))
        from installer import operations
        from installer.util import InstallerError
        target = self.base / "acl-state"
        target.mkdir()
        with mock.patch("installer.operations.os.name", "nt"), \
                mock.patch("installer.operations.shutil.which", return_value="powershell.exe"), \
                mock.patch("installer.operations.subprocess.run",
                           return_value=subprocess.CompletedProcess([], 0, "PRIVATE\n", "")):
            operations._validate_platform_home(target)
        with mock.patch("installer.operations.os.name", "nt"), \
                mock.patch("installer.operations.shutil.which", return_value="powershell.exe"), \
                mock.patch("installer.operations.subprocess.run",
                           return_value=subprocess.CompletedProcess([], 42, "", "broad ACL")):
            with self.assertRaisesRegex(InstallerError, "Windows ACL"):
                operations._validate_platform_home(target)

    def test_same_version_reinstall_is_idempotent_for_managers(self) -> None:
        first = self.install("claude-code")
        self.assertEqual(first.returncode, 0, first.stderr + first.stdout)
        before = self.mutation_log()
        second = self.install("claude-code")
        self.assertEqual(second.returncode, 0, second.stderr + second.stdout)
        self.assertEqual(self.mutation_log(), before)
        committed = [json.loads(path.read_text(encoding="utf-8")) for path in (self.home / "transactions").glob("*/journal.json")]
        self.assertEqual(sum(item["status"] == "committed" for item in committed), 2)

    def test_preexisting_same_name_marketplace_is_not_adopted_or_removed(self) -> None:
        self.state.write_text(json.dumps({
            "codex": {"marketplace": True, "plugin": False, "version": "0.1.0-beta.1"}
        }), encoding="utf-8")
        result = self.install("codex")
        self.assertEqual(result.returncode, 1, result.stderr + result.stdout)
        self.assertIn("供給元を自動採用しない", result.stderr)
        self.assertEqual(self.manager_state()["codex"],
                         {"marketplace": True, "plugin": False, "version": "0.1.0-beta.1"})
        self.assertFalse(self.home.exists())

    def test_preexisting_same_name_plugin_is_not_adopted_or_removed(self) -> None:
        self.state.write_text(json.dumps({
            "codex": {"marketplace": True, "plugin": True, "version": "0.1.0-beta.1"}
        }), encoding="utf-8")
        result = self.install("codex")
        self.assertEqual(result.returncode, 1, result.stderr + result.stdout)
        self.assertIn("供給元を自動採用しない", result.stderr)
        self.assertTrue(self.manager_state()["codex"]["plugin"])
        self.assertFalse(self.home.exists())

    def test_changed_marketplace_source_is_not_updated_or_uninstalled(self) -> None:
        self.assertEqual(self.install("codex").returncode, 0)
        state = self.manager_state()
        state["codex"]["marketplace_source"] = "https://example.invalid/other.git"
        self.state.write_text(json.dumps(state), encoding="utf-8")
        removed = self.run_cli("uninstall", "--host", "codex", "--yes")
        self.assertEqual(removed.returncode, 1, removed.stderr + removed.stdout)
        self.assertIn("供給元/ref", removed.stderr)
        self.assertTrue(self.manager_state()["codex"]["plugin"])
        newer = self.base / "tampered-source-update"
        self._make_source(newer, "0.1.0-beta.2")
        env = dict(self.env)
        env["FAKE_PLUGIN_PATH"] = str(newer / "plugins" / "kiseki-da")
        updated = self.run_cli("update", "--yes", "--source", str(newer), env=env)
        self.assertEqual(updated.returncode, 1, updated.stderr + updated.stdout)
        self.assertIn("供給元/ref", updated.stderr)

    def test_explicit_update_switches_version_and_refreshes_plugin(self) -> None:
        self.assertEqual(self.install("codex").returncode, 0)
        newer = self.base / "new-source"
        self._make_source(newer, "0.1.0-beta.2")
        env = dict(self.env)
        env["FAKE_PLUGIN_PATH"] = str(newer / "plugins" / "kiseki-da")
        result = self.run_cli("update", "--yes", "--source", str(newer), env=env)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        current = json.loads((self.home / "current.json").read_text(encoding="utf-8"))
        self.assertEqual(current["version"], "0.1.0-beta.2")
        log = "\n".join(self.mutation_log())
        self.assertIn("plugin remove kiseki-da@kiseki-da", log)
        self.assertIn("--ref v0.1.0-beta.2", log)

    def test_update_dry_run_does_not_open_network(self) -> None:
        self.assertEqual(self.install("codex").returncode, 0)
        env = dict(self.env)
        env.pop("KISEKI_DA_UPDATE_SOURCE", None)
        with mock.patch("urllib.request.urlopen", side_effect=AssertionError("network used")):
            # Run in-process so the network mock covers update_source if it is accidentally entered.
            sys.path.insert(0, str(ROOT))
            from installer.cli import main as installer_main
            old_env = os.environ.copy()
            os.environ.clear()
            os.environ.update(env)
            try:
                with mock.patch("sys.stdout"):
                    code = installer_main(["update", "--dry-run"])
            finally:
                os.environ.clear()
                os.environ.update(old_env)
        self.assertEqual(code, 0)

    def test_manager_failure_rolls_back_all_install_outputs(self) -> None:
        env = dict(self.env)
        env["FAKE_FAIL_ON"] = "claude-code plugin install"
        result = self.run_cli("install", "--host", "claude-code", "--scope", "user", "--answers", str(self.empty_answers),
                              "--yes", "--source", str(self.source), env=env)
        self.assertEqual(result.returncode, 2, result.stderr + result.stdout)
        self.assertFalse((self.home / "current.json").exists())
        self.assertFalse((self.home / "install.json").exists())
        self.assertFalse((self.home / "runtime").exists())
        self.assertFalse((self.home / "bin").exists())
        self.assertFalse((self.base / "user-scripts" / ("kiseki-da.cmd" if os.name == "nt" else "kiseki-da")).exists())
        state = self.manager_state()
        self.assertFalse(state["claude-code"]["marketplace"])
        journals = list((self.home / "transactions").glob("*/journal.json"))
        self.assertEqual(len(journals), 1)
        self.assertEqual(json.loads(journals[0].read_text(encoding="utf-8"))["status"], "rolled_back")

    def test_uninstall_preserves_user_state(self) -> None:
        self.assertEqual(self.install("claude-code").returncode, 0)
        events = self.home / "events.jsonl"
        events.write_text('{"type":"capture"}\n', encoding="utf-8")
        result = self.run_cli("uninstall", "--host", "claude-code", "--yes")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertTrue(events.is_file())
        self.assertFalse((self.home / "current.json").exists())
        self.assertFalse((self.home / "runtime").exists())
        self.assertFalse(self.manager_state()["claude-code"]["plugin"])
        metadata = json.loads((self.home / "install.json").read_text(encoding="utf-8"))
        self.assertFalse(metadata["installed"])

    @unittest.skipIf(os.name == "nt", "symlink creation requires optional Windows privilege")
    def test_symlinked_owned_launcher_blocks_uninstall_without_deleting_target(self) -> None:
        self.assertEqual(self.install("codex").returncode, 0)
        launcher = self.base / "user-scripts" / "kiseki-da"
        target = self.base / "same-content-launcher"
        target.write_bytes(launcher.read_bytes())
        os.chmod(target, 0o755)
        launcher.unlink()
        launcher.symlink_to(target)
        removed = self.run_cli("uninstall", "--host", "codex", "--yes")
        self.assertEqual(removed.returncode, 1, removed.stderr + removed.stdout)
        self.assertIn("launcherは導入後に変更", removed.stderr)
        self.assertTrue(launcher.is_symlink())
        self.assertTrue(target.is_file())
        self.assertTrue(self.manager_state()["codex"]["plugin"])

    def test_uninstall_inventory_failure_rolls_back_and_keeps_runtime(self) -> None:
        self.assertEqual(self.install("codex").returncode, 0)
        env = dict(self.env)
        env["FAKE_FAIL_INVENTORY"] = "plugin list --json"
        result = self.run_cli("uninstall", "--host", "codex", "--yes", env=env)
        self.assertEqual(result.returncode, 1, result.stderr + result.stdout)
        self.assertTrue((self.home / "current.json").is_file())
        self.assertTrue((self.home / "runtime").is_dir())
        self.assertTrue(self.manager_state()["codex"]["plugin"])

    def test_uninstall_dry_run_does_not_invoke_host_manager(self) -> None:
        self.assertEqual(self.install("codex").returncode, 0)
        before = list(self.mutation_log())
        env = dict(self.env)
        env["FAKE_FAIL_INVENTORY"] = "plugin list --json"
        result = self.run_cli("uninstall", "--host", "codex", "--dry-run", env=env)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(self.mutation_log(), before)
        self.assertTrue(Path(self.env["KISEKI_DA_POINTER"]).exists())

    def test_gui_hook_uses_safe_location_pointer_without_home_env(self) -> None:
        self.assertEqual(self.install("codex").returncode, 0)
        env = dict(self.env)
        env.pop("KISEKI_DA_HOME", None)
        env["PLUGIN_ROOT"] = str(self.source / "plugins" / "kiseki-da")
        payload = {"session_id": "gui-pointer", "cwd": str(self.base),
                   "hook_event_name": "SessionStart", "source": "startup"}
        result = subprocess.run(
            [sys.executable, str(self.source / "plugins" / "kiseki-da" / "scripts" / "hook_entry.py"),
             "session-start", "codex"],
            input=json.dumps(payload), capture_output=True, text=True, env=env, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Kiseki DA", result.stdout)
        self.assertTrue((self.home / "events.jsonl").is_file())

    def test_identical_preexisting_location_pointer_remains_user_owned(self) -> None:
        pointer = Path(self.env["KISEKI_DA_POINTER"])
        pointer.write_text(str(self.home.resolve()) + "\n", encoding="utf-8")
        os.chmod(pointer, 0o600)
        self.assertEqual(self.install("codex").returncode, 0)
        metadata = json.loads((self.home / "install.json").read_text(encoding="utf-8"))
        self.assertFalse(metadata["location_pointer"]["owned"])
        result = self.run_cli("uninstall", "--host", "codex", "--yes")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertTrue(pointer.is_file())

    def test_changed_owned_location_pointer_blocks_final_uninstall(self) -> None:
        self.assertEqual(self.install("codex").returncode, 0)
        pointer = Path(self.env["KISEKI_DA_POINTER"])
        pointer.write_text(str(self.base / "other") + "\n", encoding="utf-8")
        result = self.run_cli("uninstall", "--host", "codex", "--yes")
        self.assertEqual(result.returncode, 1)
        self.assertIn("pointerは導入後に変更", result.stderr)
        self.assertTrue(self.manager_state()["codex"]["plugin"])

    def test_doctor_detects_missing_location_pointer(self) -> None:
        self.assertEqual(self.install("claude-code").returncode, 0)
        Path(self.env["KISEKI_DA_POINTER"]).unlink()
        result = self.run_cli("doctor", "--json")
        self.assertEqual(result.returncode, 1)
        data = json.loads(result.stdout)
        pointer = next(item for item in data["checks"] if item["name"] == "location-pointer")
        self.assertEqual(pointer["status"], "error")

    def test_manual_rollback_reverts_committed_install(self) -> None:
        self.assertEqual(self.install("codex").returncode, 0)
        profile_before = (self.home / "profile.toml").read_bytes()
        (self.home / "events.jsonl").write_text('{"type":"capture","text":"after install"}\n', encoding="utf-8")
        result = self.run_cli("rollback", "--transaction", "latest", "--yes")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertFalse((self.home / "current.json").exists())
        self.assertFalse((self.home / "install.json").exists())
        self.assertFalse(self.manager_state()["codex"]["plugin"])
        self.assertEqual((self.home / "profile.toml").read_bytes(), profile_before)
        self.assertIn("after install", (self.home / "events.jsonl").read_text(encoding="utf-8"))

    def test_unfinished_transaction_blocks_mutation(self) -> None:
        active = self.home / "transactions" / "stuck"
        active.mkdir(parents=True)
        (active / "journal.json").write_text('{"id":"stuck","status":"active"}\n', encoding="utf-8")
        result = self.install("codex")
        self.assertEqual(result.returncode, 1)
        self.assertIn("未完了transaction", result.stderr)
        self.assertFalse(self.state.exists())

    def test_checksum_success_and_mismatch(self) -> None:
        archive = self.base / "kiseki-da.zip"
        archive.write_bytes(b"release")
        digest = hashlib.sha256(b"release").hexdigest()
        sums = self.base / "SHA256SUMS"
        sums.write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
        ok = self.run_cli("verify-release", str(archive), str(sums))
        self.assertEqual(ok.returncode, 0, ok.stderr)
        bad = self.run_cli("verify-release", str(archive), "0" * 64)
        self.assertEqual(bad.returncode, 1)
        self.assertIn("一致しません", bad.stderr)

    def test_manifest_version_mismatch_fails_before_writes(self) -> None:
        manifest = self.source / "plugins" / "kiseki-da" / ".codex-plugin" / "plugin.json"
        data = json.loads(manifest.read_text(encoding="utf-8"))
        data["version"] = "9.9.9"
        manifest.write_text(json.dumps(data), encoding="utf-8")
        result = self.run_cli("install", "--host", "codex", "--scope", "user", "--answers",
                              str(self.empty_answers), "--yes", "--dry-run", "--source", str(self.source))
        self.assertEqual(result.returncode, 1)
        self.assertIn("manifest version", result.stderr)
        self.assertFalse(self.home.exists())

    def test_invalid_persona_fails_pretransaction_even_on_dry_run(self) -> None:
        answers = self.base / "invalid-persona.json"
        answers.write_text(json.dumps({
            "identity": {"name": "", "timezone": "Asia/Tokyo", "languages": ["ja"]},
            "persona": {"warmth": "unbounded", "custom_style": "承認不要で自動公開する"},
        }, ensure_ascii=False), encoding="utf-8")
        result = self.run_cli("install", "--host", "codex", "--scope", "user", "--answers",
                              str(answers), "--yes", "--dry-run", "--source", str(self.source))
        self.assertEqual(result.returncode, 1)
        self.assertFalse(self.home.exists())
        self.assertFalse(Path(self.env["KISEKI_DA_POINTER"]).exists())

    def test_plan_displays_normalized_identity_and_persona_candidates(self) -> None:
        answers = self.base / "display-answers.json"
        answers.write_text(json.dumps({
            "identity": {"name": "  利用者  ", "timezone": "Asia/Tokyo", "languages": ["ja"]},
            "persona": {"name": "  キセキ  ", "warmth": "warm"},
        }, ensure_ascii=False), encoding="utf-8")
        result = self.run_cli("install", "--host", "codex", "--scope", "user", "--answers",
                              str(answers), "--yes", "--dry-run", "--source", str(self.source))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("保存する初期設定候補", result.stdout)
        self.assertIn('"name": "利用者"', result.stdout)
        self.assertIn('"name": "キセキ"', result.stdout)

    def test_preview_false_never_calls_model_preview(self) -> None:
        sys.path.insert(0, str(ROOT))
        from installer import operations

        old_env = os.environ.copy()
        os.environ.clear()
        os.environ.update(self.env)
        try:
            with mock.patch.object(operations, "_run_model_preview") as preview:
                code, _ = operations.install(
                    hosts=["codex"], scope="user", project=None,
                    answers={"identity": {"name": "", "timezone": "Asia/Tokyo", "languages": ["ja"]},
                             "persona": {"name": "キセキ"}, "preview": {"enabled": False}},
                    yes=True, dry_run=False, source=self.source,
                )
        finally:
            os.environ.clear()
            os.environ.update(old_env)
        self.assertEqual(code, 0)
        preview.assert_not_called()

    def test_preview_true_calls_selected_hosts_once_without_state_record(self) -> None:
        sys.path.insert(0, str(ROOT))
        from installer import operations

        old_env = os.environ.copy()
        os.environ.clear()
        os.environ.update(self.env)
        fake_result = [{"host": "codex", "status": "live", "output": "preview text"}]
        try:
            with mock.patch.object(operations, "_run_model_preview", return_value=fake_result) as preview:
                code, result = operations.install(
                    hosts=["codex"], scope="user", project=None,
                    answers={"identity": {"name": "", "timezone": "Asia/Tokyo", "languages": ["ja"]},
                             "persona": {"name": "キセキ"},
                             "preview": {"enabled": True, "hosts": "selected"}},
                    yes=True, dry_run=False, source=self.source,
                )
        finally:
            os.environ.clear()
            os.environ.update(old_env)
        self.assertEqual(code, 0, result)
        preview.assert_called_once()
        self.assertEqual(preview.call_args.args[2], ["codex"])
        self.assertEqual(result["preview_results"], fake_result)
        events = (self.home / "events.jsonl").read_text(encoding="utf-8") if (self.home / "events.jsonl").is_file() else ""
        self.assertNotIn("preview text", events)

    def test_hook_smoke_failure_rolls_back_install(self) -> None:
        hook_entry = self.source / "plugins" / "kiseki-da" / "scripts" / "hook_entry.py"
        hook_entry.write_text("raise SystemExit(0)\n", encoding="utf-8")
        result = self.install("codex")
        self.assertEqual(result.returncode, 2, result.stderr + result.stdout)
        self.assertFalse((self.home / "current.json").exists())
        self.assertFalse(Path(self.env["KISEKI_DA_POINTER"]).exists())
        self.assertFalse(self.manager_state()["codex"]["plugin"])

    def test_beta_update_release_selection(self) -> None:
        sys.path.insert(0, str(ROOT))
        from installer.update_source import _select_release
        rows = [
            {"draft": True, "prerelease": True, "assets": [{"name": "kiseki-da-draft.zip"}]},
            {"draft": False, "prerelease": True, "tag_name": "v0.2.0-beta.1",
             "assets": [{"name": "kiseki-da-0.2.0-beta.1.zip"}]},
            {"draft": False, "prerelease": False, "tag_name": "v0.1.0",
             "assets": [{"name": "kiseki-da-0.1.0.zip"}]},
        ]
        self.assertEqual(_select_release(rows, allow_prerelease=True)["tag_name"], "v0.2.0-beta.1")
        self.assertEqual(_select_release(rows, allow_prerelease=False)["tag_name"], "v0.1.0")

    def test_keyboard_interrupt_returns_130_and_rolls_back(self) -> None:
        sys.path.insert(0, str(ROOT))
        from installer import operations
        from installer.hosts import Inventory

        class InterruptingManager:
            host = "claude-code"

            def preflight(self):
                return {"version": "9.9.9", "executable": "fake", "features": []}

            def inventory(self):
                return Inventory(False, False, [], [])

            def marketplace_add(self, *, version=None):
                return ([sys.executable, str(self.fake), "claude-code", "plugin", "marketplace", "add", "source"],
                        [sys.executable, str(self.fake), "claude-code", "plugin", "marketplace", "remove", "kiseki-da"])

            def run(self, _argv):
                raise KeyboardInterrupt

        manager = InterruptingManager()
        manager.fake = self.fake
        old_env = os.environ.copy()
        os.environ.update(self.env)
        try:
            with mock.patch.object(operations, "HostManager", return_value=manager):
                code, result = operations.install(
                    hosts=["claude-code"], scope="user", project=None, answers={}, yes=True,
                    dry_run=False, source=self.source,
                )
        finally:
            os.environ.clear()
            os.environ.update(old_env)
        self.assertEqual(code, 130, result)
        self.assertFalse((self.home / "current.json").exists())

    def test_legacy_state_is_only_reported(self) -> None:
        legacy = self.base / "legacy-pa"
        legacy.mkdir()
        (legacy / "profile.toml").write_text("schema=1\n", encoding="utf-8")
        env = dict(self.env)
        env["PA_HOME"] = str(legacy)
        result = self.run_cli("install", "--host", "codex", "--scope", "user", "--yes", "--dry-run", "--source", str(self.source), env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("自動importしない", result.stdout)
        self.assertEqual((legacy / "profile.toml").read_text(encoding="utf-8"), "schema=1\n")

    def test_legacy_manual_adapter_is_reported_without_editing(self) -> None:
        agents = Path(self.env["CODEX_HOME"]) / "AGENTS.md"
        agents.parent.mkdir(parents=True)
        original = "Run PA_HOME/core/ctx/cli.py from pa-harness.\n"
        agents.write_text(original, encoding="utf-8")
        result = self.run_cli("install", "--host", "codex", "--scope", "user", "--answers",
                              str(self.empty_answers), "--yes", "--dry-run", "--source", str(self.source))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("旧manual adapter", result.stdout)
        self.assertIn(str(agents), result.stdout)
        self.assertEqual(agents.read_text(encoding="utf-8"), original)

    def test_explicit_legacy_import_copies_and_preserves_source(self) -> None:
        legacy = self.base / "legacy-pa"
        legacy.mkdir()
        original = ('schema = 1\n\n[identity]\nname = "旧利用者"\ntimezone = "Asia/Tokyo"\n'
                    'languages = ["ja"]\n\n[da]\nname = "旧DA"\n')
        (legacy / "profile.toml").write_text(original, encoding="utf-8")
        (legacy / "events.jsonl").write_text('{"type":"capture","text":"legacy"}\n', encoding="utf-8")
        env = dict(self.env)
        env["PA_HOME"] = str(legacy)
        result = self.run_cli("install", "--host", "codex", "--scope", "user", "--answers",
                              str(self.empty_answers), "--yes", "--import-legacy", "--source", str(self.source), env=env)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual((legacy / "profile.toml").read_text(encoding="utf-8"), original)
        self.assertTrue((self.home / "events.jsonl").is_file())

    def test_answers_configure_bounded_persona(self) -> None:
        answers = self.base / "answers.json"
        answers.write_text(json.dumps({
            "host": "claude-code",
            "scope": "user",
            "identity": {"name": "利用者"},
            "persona": {
                "name": "キセキ",
                "first_person": "私",
                "user_address": "利用者さん",
                "formality": "balanced",
                "warmth": "warm",
                "verbosity": "compact",
                "initiative": "balanced",
                "relationship": "partner",
                "custom_style": "率直で落ち着いた共同設計者として話す",
            },
        }, ensure_ascii=False), encoding="utf-8")
        result = self.run_cli("install", "--answers", str(answers), "--yes", "--source", str(self.source))
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        import tomllib
        with (self.home / "profile.toml").open("rb") as stream:
            profile = tomllib.load(stream)
        self.assertEqual(profile["schema"], 2)
        self.assertEqual(profile["identity"]["name"], "利用者")
        self.assertEqual(profile["persona"]["name"], "キセキ")

    def test_persona_edit_is_transactional_and_explicitly_rollbackable(self) -> None:
        self.assertEqual(self.install("codex").returncode, 0)
        launcher = self.home / "bin" / "kiseki-da.py"
        before = (self.home / "profile.toml").read_bytes()
        edited = subprocess.run(
            [sys.executable, str(launcher), "persona", "edit", "--name", "キセキ", "--yes"],
            env=self.env, capture_output=True, text=True, check=False,
        )
        self.assertEqual(edited.returncode, 0, edited.stderr + edited.stdout)
        self.assertIn("transaction:", edited.stdout)
        self.assertIn('name = "キセキ"', (self.home / "profile.toml").read_text(encoding="utf-8"))
        rolled_back = self.run_cli("rollback", "--transaction", "latest", "--yes")
        self.assertEqual(rolled_back.returncode, 0, rolled_back.stderr + rolled_back.stdout)
        self.assertEqual((self.home / "profile.toml").read_bytes(), before)

    def test_noninteractive_install_requires_complete_answers(self) -> None:
        result = self.run_cli("install", "--host", "codex", "--scope", "user", "--yes",
                              "--source", str(self.source))
        self.assertEqual(result.returncode, 1)
        self.assertIn("完全な--answers", result.stderr)
        self.assertFalse(self.home.exists())

    def test_planned_nested_answers_shape(self) -> None:
        project = self.base / "nested-project"
        project.mkdir()
        answers = self.base / "nested-answers.json"
        answers.write_text(json.dumps({
            "schema": 1,
            "hosts": ["codex"],
            "activation": {"mode": "project", "projects": [{
                "path": str(project), "persona": {"name": "案件キセキ", "relationship": "partner"},
            }]},
            "identity": {"name": "利用者", "timezone": "Asia/Tokyo", "languages": ["ja"]},
            "security": {"apply_recommended_host_settings": False},
            "preview": {"enabled": False, "hosts": "selected", "max_rounds": 3},
        }, ensure_ascii=False), encoding="utf-8")
        result = self.run_cli("install", "--answers", str(answers), "--yes", "--source", str(self.source))
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        registry = json.loads((self.home / "projects.json").read_text(encoding="utf-8"))
        project_profile = self.home / "projects" / registry["projects"][0]["id"] / "profile.toml"
        self.assertIn('name = "案件キセキ"', project_profile.read_text(encoding="utf-8"))

    def test_project_scope_stores_persona_in_project_only(self) -> None:
        project = self.base / "案件 日本語"
        project.mkdir()
        answers = self.base / "project-answers.json"
        answers.write_text(json.dumps({
            "host": "codex", "scope": "project", "project": str(project),
            "identity": {"name": "共通利用者"},
            "persona": {"name": "案件専用", "relationship": "partner"},
        }, ensure_ascii=False), encoding="utf-8")
        result = self.run_cli("install", "--answers", str(answers), "--yes", "--source", str(self.source))
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        registry = json.loads((self.home / "projects.json").read_text(encoding="utf-8"))
        self.assertEqual(registry["mode"], "project")
        self.assertEqual(len(registry["projects"]), 1)
        import tomllib
        with (self.home / "profile.toml").open("rb") as stream:
            common = tomllib.load(stream)
        with (self.home / "projects" / registry["projects"][0]["id"] / "profile.toml").open("rb") as stream:
            scoped = tomllib.load(stream)
        self.assertEqual(common["identity"]["name"], "共通利用者")
        self.assertFalse(common.get("persona"))
        self.assertEqual(scoped["persona"]["name"], "案件専用")

    def test_codex_project_scope_plan_states_local_only_limitation(self) -> None:
        project = self.base / "codex-local-project"
        project.mkdir()
        result = self.run_cli(
            "install", "--host", "codex", "--scope", "project", "--project", str(project),
            "--dry-run", "--source", str(self.source),
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("Local環境限定", result.stdout)
        self.assertIn("管理Worktree/Cloudではactivateしません", result.stdout)

    def test_project_registry_remains_authoritative_across_update(self) -> None:
        self.assertEqual(self.install("codex").returncode, 0)
        project_a = self.base / "project-a"
        project_b = self.base / "project-b"
        project_a.mkdir()
        project_b.mkdir()
        launcher = self.home / "bin" / "kiseki-da.py"
        for project in (project_a, project_b):
            added = subprocess.run(
                [sys.executable, str(launcher), "project", "add", str(project), "--yes"],
                env=self.env, capture_output=True, text=True, check=False,
            )
            self.assertEqual(added.returncode, 0, added.stderr)
        newer = self.base / "scope-update-source"
        self._make_source(newer, "0.1.0-beta.2")
        env = dict(self.env)
        env["FAKE_PLUGIN_PATH"] = str(newer / "plugins" / "kiseki-da")
        updated = self.run_cli("update", "--yes", "--source", str(newer), env=env)
        self.assertEqual(updated.returncode, 0, updated.stderr + updated.stdout)
        registry = json.loads((self.home / "projects.json").read_text(encoding="utf-8"))
        self.assertEqual(registry["mode"], "project")
        self.assertEqual({row["path"] for row in registry["projects"]},
                         {str(project_a.resolve()), str(project_b.resolve())})
        metadata = json.loads((self.home / "install.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["scope"], "project")
        self.assertEqual(set(metadata["projects"]), {str(project_a.resolve()), str(project_b.resolve())})

    def test_empty_project_registry_is_not_changed_to_user_or_cwd_on_update(self) -> None:
        project = self.base / "temporary-project"
        project.mkdir()
        answers = self.base / "empty-project-mode.json"
        answers.write_text(json.dumps({
            "hosts": ["codex"], "activation": {"mode": "project", "projects": [{"path": str(project)}]},
            "identity": {"name": "", "timezone": "Asia/Tokyo", "languages": ["ja"]}, "persona": {},
        }), encoding="utf-8")
        installed = self.run_cli("install", "--answers", str(answers), "--yes", "--source", str(self.source))
        self.assertEqual(installed.returncode, 0, installed.stderr + installed.stdout)
        launcher = self.home / "bin" / "kiseki-da.py"
        removed = subprocess.run(
            [sys.executable, str(launcher), "project", "remove", str(project), "--yes"],
            env=self.env, capture_output=True, text=True, check=False,
        )
        self.assertEqual(removed.returncode, 0, removed.stderr)
        newer = self.base / "empty-scope-update-source"
        self._make_source(newer, "0.1.0-beta.2")
        env = dict(self.env)
        env["FAKE_PLUGIN_PATH"] = str(newer / "plugins" / "kiseki-da")
        updated = self.run_cli("update", "--yes", "--source", str(newer), env=env)
        self.assertEqual(updated.returncode, 0, updated.stderr + updated.stdout)
        registry = json.loads((self.home / "projects.json").read_text(encoding="utf-8"))
        self.assertEqual(registry, {"schema": 1, "mode": "project", "projects": []})

    def test_codex_doctor_requires_explicit_hash_attestation(self) -> None:
        self.assertEqual(self.install("codex").returncode, 0)
        actual_hook = self.source / "plugins" / "kiseki-da" / "hooks" / "hooks.json"
        expected = hashlib.sha256(actual_hook.read_bytes()).hexdigest()
        runtime = Path(json.loads((self.home / "current.json").read_text(encoding="utf-8"))["runtime"])
        runtime_hook = runtime / "plugins" / "kiseki-da" / "hooks" / "hooks.json"
        runtime_hook.write_text(runtime_hook.read_text(encoding="utf-8") + " ", encoding="utf-8")
        pending = self.run_cli("doctor", "--json")
        self.assertEqual(pending.returncode, 1)
        self.assertEqual(json.loads(pending.stdout)["status"], "pending_activation")
        confirmed = self.run_cli("doctor", "--confirm-codex-trust", "--yes", "--json")
        self.assertEqual(confirmed.returncode, 0, confirmed.stderr + confirmed.stdout)
        self.assertEqual(json.loads(confirmed.stdout)["status"], "healthy")
        record = json.loads((self.home / "install" / "codex-hook-trust.json").read_text(encoding="utf-8"))
        self.assertEqual(record["hook_sha256"], expected)
        self.assertEqual(record["plugin_path"], str((self.source / "plugins" / "kiseki-da").resolve()))
        actual_hook.write_text(actual_hook.read_text(encoding="utf-8") + " ", encoding="utf-8")
        changed = self.run_cli("doctor", "--json")
        self.assertEqual(changed.returncode, 1)
        self.assertEqual(json.loads(changed.stdout)["status"], "pending_activation")

    def test_codex_install_rolls_back_when_manager_reports_no_installed_path(self) -> None:
        env = dict(self.env)
        env.pop("FAKE_PLUGIN_PATH", None)
        result = self.run_cli("install", "--host", "codex", "--scope", "user", "--answers",
                              str(self.empty_answers), "--yes", "--source", str(self.source), env=env)
        self.assertEqual(result.returncode, 2, result.stderr + result.stdout)
        self.assertIn("installed plugin path", result.stderr)
        self.assertFalse((self.home / "current.json").exists())
        self.assertFalse(self.manager_state()["codex"]["plugin"])

    def test_explicit_security_defaults_are_reversible(self) -> None:
        config = Path(self.env["CODEX_HOME"]) / "config.toml"
        config.parent.mkdir(parents=True)
        original = 'model = "gpt-test"\n\n[projects."/tmp/demo"]\ntrusted = true\n'
        config.write_text(original, encoding="utf-8")
        result = self.run_cli(
            "install", "--host", "codex", "--scope", "user", "--host-security", "recommended",
            "--answers", str(self.empty_answers), "--yes", "--source", str(self.source),
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        applied = config.read_text(encoding="utf-8")
        self.assertIn('approval_policy = "on-request"', applied.split("[projects", 1)[0])
        self.assertIn('sandbox_mode = "workspace-write"', applied.split("[projects", 1)[0])
        result = self.run_cli("uninstall", "--host", "codex", "--yes")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(config.read_text(encoding="utf-8"), original)

    def test_security_restore_refuses_to_overwrite_user_change(self) -> None:
        config = Path(self.env["CODEX_HOME"]) / "config.toml"
        config.parent.mkdir(parents=True)
        config.write_text('model = "before"\n', encoding="utf-8")
        result = self.run_cli(
            "install", "--host", "codex", "--scope", "user", "--host-security", "recommended",
            "--answers", str(self.empty_answers), "--yes", "--source", str(self.source),
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        config.write_text(config.read_text(encoding="utf-8") + "# user edit\n", encoding="utf-8")
        result = self.run_cli("uninstall", "--host", "codex", "--yes")
        self.assertEqual(result.returncode, 1)
        self.assertIn("uninstallを停止", result.stderr)
        self.assertTrue(self.manager_state()["codex"]["plugin"])

    def test_security_change_rolls_back_when_plugin_install_fails(self) -> None:
        config = Path(self.env["CLAUDE_CONFIG_DIR"]) / "settings.json"
        config.parent.mkdir(parents=True)
        original = '{"model":"test"}\n'
        config.write_text(original, encoding="utf-8")
        env = dict(self.env)
        env["FAKE_FAIL_ON"] = "claude-code plugin install"
        result = self.run_cli(
            "install", "--host", "claude-code", "--scope", "user", "--host-security", "recommended",
            "--answers", str(self.empty_answers), "--yes", "--source", str(self.source), env=env,
        )
        self.assertEqual(result.returncode, 2, result.stderr + result.stdout)
        self.assertEqual(config.read_text(encoding="utf-8"), original)

    def test_recommended_security_refreshes_after_manager_update_and_uninstalls_cleanly(self) -> None:
        config = Path(self.env["CLAUDE_CONFIG_DIR"]) / "settings.json"
        config.parent.mkdir(parents=True)
        original = '{"model":"test"}\n'
        config.write_text(original, encoding="utf-8")
        env = dict(self.env)
        env["FAKE_CLAUDE_SETTINGS"] = str(config)
        first = self.run_cli(
            "install", "--host", "claude-code", "--scope", "user", "--host-security", "recommended",
            "--answers", str(self.empty_answers), "--yes", "--source", str(self.source), env=env,
        )
        self.assertEqual(first.returncode, 0, first.stderr + first.stdout)
        newer = self.base / "security-update-source"
        self._make_source(newer, "0.1.0-beta.2")
        env["KISEKI_DA_UPDATE_SOURCE"] = str(newer)
        env["FAKE_PLUGIN_PATH"] = str(newer / "plugins" / "kiseki-da")
        updated = self.run_cli("update", "--yes", "--source", str(newer), env=env)
        self.assertEqual(updated.returncode, 0, updated.stderr + updated.stdout)
        applied = json.loads(config.read_text(encoding="utf-8"))
        self.assertTrue(applied["fakeNativePlugins"]["kiseki-da"])
        self.assertEqual(applied["permissions"]["defaultMode"], "default")
        removed = self.run_cli("uninstall", "--host", "claude-code", "--yes", env=env)
        self.assertEqual(removed.returncode, 0, removed.stderr + removed.stdout)
        self.assertEqual(json.loads(config.read_text(encoding="utf-8")), {"model": "test"})

    def test_recommended_security_can_be_reinstalled_after_uninstall(self) -> None:
        config = Path(self.env["CODEX_HOME"]) / "config.toml"
        config.parent.mkdir(parents=True)
        config.write_text('model = "before"\n', encoding="utf-8")
        args = (
            "install", "--host", "codex", "--scope", "user", "--host-security", "recommended",
            "--answers", str(self.empty_answers), "--yes", "--source", str(self.source),
        )
        first = self.run_cli(*args)
        self.assertEqual(first.returncode, 0, first.stderr + first.stdout)
        removed = self.run_cli("uninstall", "--host", "codex", "--yes")
        self.assertEqual(removed.returncode, 0, removed.stderr + removed.stdout)
        self.assertFalse((self.home / "security-backups" / "codex" / "record.json").exists())
        second = self.run_cli(*args)
        self.assertEqual(second.returncode, 0, second.stderr + second.stdout)

    def test_manual_rollback_preserves_concurrent_external_edit(self) -> None:
        sys.path.insert(0, str(ROOT))
        from installer.hosts import run_command
        from installer.transaction import Transaction, rollback_saved
        target = self.base / "external-settings.json"
        target.write_text("original\n", encoding="utf-8")
        tx = Transaction(self.home, "test-concurrent")
        tx.write_external_text(target, "installer\n")
        tx.commit()
        target.write_text("user edit\n", encoding="utf-8")
        _, ok, errors = rollback_saved(self.home, "latest", run_command)
        self.assertFalse(ok)
        self.assertTrue(any("変更を検出" in error for error in errors))
        self.assertEqual(target.read_text(encoding="utf-8"), "user edit\n")

    def test_failed_external_step_is_still_undone(self) -> None:
        sys.path.insert(0, str(ROOT))
        from installer.transaction import Transaction
        from installer.util import InstallerError
        state = {"applied": False}

        def runner(argv):
            if argv[0] == "do":
                state["applied"] = True
                return subprocess.CompletedProcess(argv, 9, "", "failed after partial apply")
            state["applied"] = False
            return subprocess.CompletedProcess(argv, 0, "", "")

        tx = Transaction(self.home, "partial-external")
        with self.assertRaises(InstallerError):
            tx.external(["do"], ["undo"], runner)
        self.assertTrue(tx.rollback(runner))
        self.assertFalse(state["applied"])


if __name__ == "__main__":
    unittest.main()
