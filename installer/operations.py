"""High-level install, update, uninstall, doctor, and rollback operations."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import sysconfig
import tempfile
from pathlib import Path
from typing import Any, Callable

from .constants import HOSTS, MARKETPLACE_ID, PLUGIN_ID, PRODUCT, SOURCE_ROOT, VERSION
from .hosts import HostManager, expand_hosts, run_command
from . import security as host_security_mod
from .transaction import Transaction, active_transactions, rollback_saved
from .util import (
    InstallerError,
    command_display,
    copytree_filtered,
    kiseki_home,
    kiseki_pointer_path,
    location_pointer_text,
    read_json,
    remove_path,
    sha256_file,
)


def _source_version(source: Path) -> str:
    try:
        value = (source / "VERSION").read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise InstallerError(f"VERSIONを読めません: {exc}") from None
    if not value or any(ch.isspace() for ch in value):
        raise InstallerError("VERSIONの形式が不正です。")
    return value


def _validate_platform_home(home: Path) -> None:
    is_wsl = bool(os.environ.get("WSL_DISTRO_NAME") or "microsoft" in platform.release().casefold())
    if is_wsl and len(home.parts) >= 3 and home.parts[1] == "mnt":
        raise InstallerError("WSLでは/mnt/<drive>配下をKISEKI_DA_HOMEにできません。")
    if os.name == "nt":
        probe = home
        while not probe.exists() and probe.parent != probe:
            probe = probe.parent
        powershell = shutil.which("powershell.exe") or shutil.which("pwsh.exe")
        if not powershell:
            raise InstallerError("Windows state ACLを検証するPowerShellがありません。")
        script = (
            "$p=$args[0];$bad=@((Get-Acl -LiteralPath $p).Access|Where-Object{"
            "try{$s=$_.IdentityReference.Translate([System.Security.Principal.SecurityIdentifier]).Value}"
            "catch{$s=$_.IdentityReference.Value};"
            "$b=$s -in @('S-1-1-0','S-1-5-11','S-1-5-32-545');"
            "$w=[int64]([System.Security.AccessControl.FileSystemRights]::Write -bor "
            "[System.Security.AccessControl.FileSystemRights]::Read -bor "
            "[System.Security.AccessControl.FileSystemRights]::ReadAndExecute -bor "
            "[System.Security.AccessControl.FileSystemRights]::ListDirectory -bor "
            "[System.Security.AccessControl.FileSystemRights]::Modify -bor "
            "[System.Security.AccessControl.FileSystemRights]::FullControl -bor "
            "[System.Security.AccessControl.FileSystemRights]::CreateFiles -bor "
            "[System.Security.AccessControl.FileSystemRights]::CreateDirectories -bor "
            "[System.Security.AccessControl.FileSystemRights]::Delete);"
            "$b -and $_.AccessControlType -eq 'Allow' -and (([int64]$_.FileSystemRights -band $w)-ne 0)"
            "});if($bad.Count){exit 42}else{'PRIVATE'}"
        )
        checked = subprocess.run(
            [powershell, "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", script, str(probe)],
            capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
        )
        if checked.returncode != 0 or "PRIVATE" not in checked.stdout:
            raise InstallerError(
                f"KISEKI_DA_HOMEが継承するWindows ACLをprivateと確認できません: {probe}"
            )


def preflight_source(source: Path, hosts: list[str]) -> dict[str, Any]:
    if not ((3, 11) <= sys.version_info[:2] <= (3, 14)):
        raise InstallerError("Python 3.11〜3.14が必要です。")
    if not (source / "install.py").is_file():
        raise InstallerError(f"install.pyがありません: {source}")
    if not (source / "plugins" / "kiseki-da" / "core" / "ctx" / "cli.py").is_file():
        raise InstallerError("plugin runtimeがありません。")
    version = _source_version(source)
    manifest_paths = {
        "claude-code": source / ".claude-plugin" / "marketplace.json",
        "codex": source / ".agents" / "plugins" / "marketplace.json",
    }
    documents: dict[str, dict] = {}
    required = {
        **manifest_paths,
        "claude-plugin": source / "plugins" / "kiseki-da" / ".claude-plugin" / "plugin.json",
        "codex-plugin": source / "plugins" / "kiseki-da" / ".codex-plugin" / "plugin.json",
    }
    for name, path in required.items():
        if not path.is_file():
            raise InstallerError(f"{name} manifestがありません: {path}")
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise InstallerError(f"manifestを読めません: {path}: {exc}") from None
        if not isinstance(value, dict):
            raise InstallerError(f"manifestはJSONオブジェクトである必要があります: {path}")
        documents[name] = value
    claude_entries = documents["claude-code"].get("plugins", [])
    claude_entry = next((row for row in claude_entries if isinstance(row, dict) and row.get("name") == PLUGIN_ID), None)
    versions = {
        "Claude marketplace": documents["claude-code"].get("version"),
        "Claude marketplace plugin": claude_entry.get("version") if claude_entry else None,
        "Claude plugin": documents["claude-plugin"].get("version"),
        "Codex plugin": documents["codex-plugin"].get("version"),
    }
    mismatched = [f"{name}={value!r}" for name, value in versions.items() if value != version]
    if mismatched:
        raise InstallerError(f"VERSION ({version}) とmanifest versionが一致しません: " + ", ".join(mismatched))
    if "hooks" in documents["codex-plugin"]:
        raise InstallerError("Codex plugin manifestにhooks keyを置くことはできません。")
    plugin_root = source / "plugins" / "kiseki-da"
    claude_hook_value = documents["claude-plugin"].get("hooks")
    if not isinstance(claude_hook_value, str):
        raise InstallerError("Claude plugin manifestのhooks pathがありません。")
    claude_hook = (plugin_root / claude_hook_value).resolve(strict=False)
    try:
        claude_hook.relative_to(plugin_root.resolve())
    except ValueError:
        raise InstallerError("Claude hook pathがplugin外を指しています。") from None
    hook_files = [claude_hook, plugin_root / "hooks" / "hooks.json"]
    for hook_file in hook_files:
        try:
            hook_value = json.loads(hook_file.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise InstallerError(f"hook定義を読めません: {hook_file}: {exc}") from None
        if not isinstance(hook_value, dict):
            raise InstallerError(f"hook定義はJSONオブジェクトである必要があります: {hook_file}")
    if not (plugin_root / "scripts" / "hook_entry.py").is_file():
        raise InstallerError("plugin hook launcherがありません。")
    return {"version": version, "source": str(source), "manifests": [str(path) for path in required.values()]}


def _validate_setup_answers(source: Path, answers: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize every value that can be persisted, before Transaction begins."""
    normalized = dict(answers)
    plugin = source / "plugins" / "kiseki-da"
    sys.path.insert(0, str(plugin))
    try:
        from core.ctx.cli import _validate_identity
        from core.ctx.persona import validate_persona
        from core.ctx.store import UserError
    except Exception as exc:  # noqa: BLE001 - a malformed release must fail before writes
        raise InstallerError(f"runtime validatorを読めません: {type(exc).__name__}: {exc}") from None
    try:
        if "identity" in answers:
            normalized["identity"] = _validate_identity(answers["identity"])
        if "persona" in answers:
            normalized["persona"] = validate_persona(answers["persona"])
    except UserError as exc:
        raise InstallerError(str(exc)) from None
    finally:
        try:
            sys.path.remove(str(plugin))
        except ValueError:
            pass
    return normalized


def _preview_request(answers: dict[str, Any], selected_hosts: list[str]) -> dict[str, Any]:
    raw = answers.get("preview")
    if raw is None:
        return {"enabled": False, "hosts": selected_hosts}
    if not isinstance(raw, dict):
        raise InstallerError("answers.previewはJSONオブジェクトで指定してください。")
    enabled = raw.get("enabled", False)
    if not isinstance(enabled, bool):
        raise InstallerError("answers.preview.enabledはtrue/falseで指定してください。")
    requested = raw.get("hosts", "selected")
    if requested == "selected" or requested is None:
        hosts = list(selected_hosts)
    elif requested == "all":
        hosts = list(HOSTS)
    elif isinstance(requested, list) and requested and all(isinstance(item, str) for item in requested):
        hosts = expand_hosts(requested)
    else:
        raise InstallerError("answers.preview.hostsはselected/allまたはhost配列で指定してください。")
    return {"enabled": enabled, "hosts": hosts}


def _run_model_preview(source: Path, persona: dict[str, Any], hosts: list[str]) -> list[dict]:
    """Run the runtime's stateless, tool-disabled preview after explicit consent."""
    plugin = source / "plugins" / "kiseki-da"
    sys.path.insert(0, str(plugin))
    try:
        from core.ctx.cli import _live_preview, _print_preview

        results = _live_preview(persona, hosts)
        _print_preview(results)
        return results
    except Exception as exc:  # noqa: BLE001 - preview failure must not block install
        fallback = [{"host": host, "status": "fallback", "output": "Kiseki DA: 設定候補を保存できます。",
                     "reason": f"{type(exc).__name__}: {exc}"} for host in hosts]
        for item in fallback:
            print(f"\n--- {item['host']} (fallback) ---\n{item['output']}\n補足: {item['reason']}")
        return fallback
    finally:
        try:
            sys.path.remove(str(plugin))
        except ValueError:
            pass


def _runtime_source(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True)
    copytree_filtered(source / "installer", destination / "installer")
    copytree_filtered(source / "plugins", destination / "plugins")
    for metadata_dir in (".claude-plugin", ".agents"):
        candidate = source / metadata_dir
        if candidate.is_dir():
            copytree_filtered(candidate, destination / metadata_dir)
    shutil.copy2(source / "install.py", destination / "install.py")
    shutil.copy2(source / "VERSION", destination / "VERSION")


def _sh_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def _cmd_quote(value: str) -> str:
    return subprocess.list2cmdline([value])


def _user_scripts_dir() -> Path:
    override = os.environ.get("KISEKI_DA_SCRIPTS_DIR")
    if override:
        return Path(override).expanduser().resolve()
    scheme = "nt_user" if os.name == "nt" else ("osx_framework_user" if sys.platform == "darwin" else "posix_user")
    return Path(sysconfig.get_path("scripts", scheme=scheme)).expanduser().resolve()


def _write_launchers(tx: Transaction, home: Path, runtime: Path, previous: dict[str, Any]) -> tuple[list[Path], list[dict]]:
    assets = runtime / "installer" / "assets"
    target_dir = home / "bin"
    bootstrap = target_dir / "kiseki-da.py"
    py = Path(sys.executable).resolve()
    tx.write_text(bootstrap, (assets / "kiseki-da.py.tmpl").read_text(encoding="utf-8"), mode=0o755)
    shell = (assets / "kiseki-da.sh.tmpl").read_text(encoding="utf-8")
    shell = shell.replace("__PYTHON__", _sh_quote(str(py))).replace("__BOOTSTRAP__", _sh_quote(str(bootstrap)))
    tx.write_text(target_dir / "kiseki-da", shell, mode=0o755)
    cmd = (assets / "kiseki-da.cmd.tmpl").read_text(encoding="utf-8")
    cmd = cmd.replace("__PYTHON__", _cmd_quote(str(py))).replace("__BOOTSTRAP__", _cmd_quote(str(bootstrap)))
    tx.write_text(target_dir / "kiseki-da.cmd", cmd)
    local_paths = [bootstrap, target_dir / "kiseki-da", target_dir / "kiseki-da.cmd"]
    public_name = "kiseki-da.cmd" if os.name == "nt" else "kiseki-da"
    public_text = cmd if os.name == "nt" else shell
    public_path = _user_scripts_dir() / public_name
    owned = {str(item.get("path")): item.get("sha256") for item in previous.get("launchers", [])
             if isinstance(item, dict)}
    if public_path.is_symlink():
        raise InstallerError(f"symlinkの同名launcherを上書きしません: {public_path}")
    if public_path.exists() and public_path.read_text(encoding="utf-8") != public_text:
        if owned.get(str(public_path)) != sha256_file(public_path):
            raise InstallerError(f"既存の同名launcherを上書きしません: {public_path}")
    tx.write_external_text(public_path, public_text, mode=0o755 if os.name != "nt" else None)
    records = [{"path": str(public_path), "sha256": sha256_file(public_path), "kind": "file"}]
    return [*local_paths, public_path], records


def _location_pointer_plan(home: Path, previous: dict[str, Any]) -> dict[str, Any]:
    path = kiseki_pointer_path()
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise InstallerError(f"KISEKI_DA_HOME pointerが通常ファイルではありません: {path}")
    text = location_pointer_text(home)
    expected = hashlib.sha256(text.encode("utf-8")).hexdigest()
    current = path.read_bytes() if path.is_file() else None
    current_hash = hashlib.sha256(current).hexdigest() if current is not None else None
    old = previous.get("location_pointer")
    old_owned = (isinstance(old, dict) and old.get("owned") is True
                 and Path(str(old.get("path", ""))).resolve(strict=False) == path
                 and old.get("sha256") == current_hash)
    if current is not None and current != text.encode("utf-8") and not old_owned:
        raise InstallerError(f"既存のKISEKI_DA_HOME pointerを上書きしません: {path}")
    # An identical pre-existing pointer is useful but remains user-owned.  We
    # therefore never delete it on uninstall unless an earlier transaction
    # recorded that Kiseki DA created it.
    owned = bool(old_owned or current is None)
    return {
        "path": str(path),
        "sha256": expected,
        "owned": owned,
        "write": current is None or current != text.encode("utf-8"),
        "text": text,
    }


def _write_location_pointer(tx: Transaction, plan: dict[str, Any]) -> dict[str, Any]:
    path = Path(plan["path"])
    if plan.get("write"):
        tx.write_external_text(path, str(plan["text"]), mode=0o600)
    return {key: plan[key] for key in ("path", "sha256", "owned")}


def _validate_owned_pointer(record: object) -> Path | None:
    if not isinstance(record, dict) or record.get("owned") is not True:
        return None
    path = Path(str(record.get("path", ""))).expanduser().absolute()
    if path != kiseki_pointer_path():
        raise InstallerError(f"pointer pathが現在のKISEKI_DA_POINTERと一致しません: {path}")
    if path.is_symlink() or (path.exists() and (not path.is_file() or sha256_file(path) != record.get("sha256"))):
        raise InstallerError(f"KISEKI_DA_HOME pointerは導入後に変更されています。自動削除しません: {path}")
    return path


def _runtime_cli(runtime: Path, argv: list[str], home: Path, *, input_text: str | None = None) -> None:
    cli = runtime / "plugins" / "kiseki-da" / "core" / "ctx" / "cli.py"
    env = os.environ.copy()
    env["KISEKI_DA_HOME"] = str(home)
    result = subprocess.run(
        [sys.executable, str(cli), *argv],
        input=input_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or str(result.returncode)).strip()
        raise InstallerError(f"runtime設定に失敗しました: {detail}")


def _configure_runtime(
    tx: Transaction,
    runtime: Path,
    home: Path,
    *,
    answers: dict[str, Any],
    yes: bool,
    scope: str,
    project: Path | None,
    hosts: list[str],
) -> None:
    for name in (
        "profile.toml", "projects.json", "project-registry.json", "activation.json", "projects",
        "tasks", "archive", "snapshots", "session", "events.jsonl", "candidates.jsonl",
    ):
        tx.backup(home / name)
    if not (home / "profile.toml").exists():
        _runtime_cli(runtime, ["init"], home)
    setup_answers = {key: answers[key] for key in ("identity", "persona") if key in answers}
    plugin = runtime / "plugins" / "kiseki-da"
    sys.path.insert(0, str(plugin))
    os.environ["KISEKI_DA_HOME"] = str(home)
    from core.ctx.persona import save_persona
    from core.ctx.scope import add_project, scoped_store, set_mode
    from core.ctx.store import Store

    common_store = Store(home=home)
    identity = setup_answers.get("identity")
    if identity is not None:
        if not isinstance(identity, dict):
            raise InstallerError("answers.identityはJSONオブジェクトで指定してください。")
        profile = common_store.read_profile()
        profile["identity"] = {**profile.get("identity", {}), **identity}
        common_store.write_profile(profile)
    set_mode(home, scope)
    if scope == "project" and project is not None:
        add_project(home, project)
    persona = setup_answers.get("persona")
    persona_store = common_store if scope == "user" else scoped_store(home, project)
    if persona is not None and persona_store is None:
        raise InstallerError("project scopeのキャラクター保存先を解決できません。")
    if persona is not None:
        if not isinstance(persona, dict):
            raise InstallerError("answers.personaはJSONオブジェクトで指定してください。")
        save_persona(persona_store, persona, merge=False)
    elif not yes:
        from core.ctx.cli import main as runtime_main

        old_cwd = Path.cwd()
        try:
            if scope == "project" and project is not None:
                os.chdir(project)
            setup_argv = ["setup"]
            for host in hosts:
                setup_argv.extend(["--host", host])
            setup_code = int(runtime_main(setup_argv) or 0)
            if setup_code == 130:
                raise KeyboardInterrupt
            if setup_code != 0:
                raise InstallerError("対話式setupに失敗しました。")
        finally:
            os.chdir(old_cwd)


def _smoke_runtime(runtime: Path, hosts: list[str]) -> None:
    """Exercise the copied hook/runtime against disposable state before commit."""
    plugin = runtime / "plugins" / "kiseki-da"
    hook_entry = plugin / "scripts" / "hook_entry.py"
    cli = plugin / "core" / "ctx" / "cli.py"
    with tempfile.TemporaryDirectory(prefix="kiseki-da-hook-smoke-") as raw:
        root = Path(raw)
        state = root / "state"
        work = root / "workspace"
        work.mkdir()
        env = os.environ.copy()
        env["KISEKI_DA_HOME"] = str(state)
        env["PLUGIN_ROOT"] = str(plugin)
        initialized = subprocess.run(
            [sys.executable, str(cli), "init"], capture_output=True, text=True,
            encoding="utf-8", errors="replace", env=env, check=False,
        )
        if initialized.returncode != 0:
            raise InstallerError("runtime hook smokeのinitに失敗しました: " +
                                 (initialized.stderr or initialized.stdout).strip())
        for host in hosts:
            payload = {
                "session_id": f"install-smoke-{host}",
                "cwd": str(work),
                "hook_event_name": "SessionStart",
                "source": "startup",
            }
            result = subprocess.run(
                [sys.executable, str(hook_entry), "session-start", host],
                input=json.dumps(payload), capture_output=True, text=True,
                encoding="utf-8", errors="replace", env=env, check=False,
            )
            if result.returncode != 0 or "Kiseki DA" not in result.stdout:
                detail = (result.stderr or result.stdout or f"exit {result.returncode}").strip()
                raise InstallerError(f"{host} runtime hook smokeに失敗しました: {detail}")


def _metadata(home: Path) -> dict[str, Any]:
    value = read_json(home / "install.json", {})
    return value if isinstance(value, dict) else {}


def _legacy_home() -> Path | None:
    raw = os.environ.get("PA_HOME")
    path = Path(raw).expanduser().resolve() if raw else (Path.home() / ".pa").resolve()
    return path if path.is_dir() and path != kiseki_home() else None


def _legacy_adapter_paths() -> list[str]:
    claude_root = Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude")).expanduser()
    codex_root = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()
    candidates = (
        claude_root / "CLAUDE.md", claude_root / "settings.json", claude_root / "hooks.json",
        codex_root / "AGENTS.md", codex_root / "hooks.json", codex_root / "config.toml",
    )
    markers = ("pa-harness", "PA_HOME", "core/ctx/cli.py")
    found: list[str] = []
    for path in candidates:
        try:
            if path.is_symlink() or not path.is_file() or path.stat().st_size > 2 * 1024 * 1024:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if any(marker in text for marker in markers):
            found.append(str(path.resolve(strict=False)))
    return found


def _import_legacy(tx: Transaction, source: Path, destination: Path) -> None:
    names = ("profile.toml", "events.jsonl", "candidates.jsonl", "tasks", "archive", "snapshots", "session")
    for name in names:
        src, dst = source / name, destination / name
        if not src.exists() and not src.is_symlink():
            continue
        if src.is_dir():
            tx.replace_tree(src, dst)
        elif src.is_file():
            tx.backup(dst)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)


def _manager_steps(
    tx: Transaction,
    manager: HostManager,
    *,
    replacing: bool,
    old_version: str | None,
    new_version: str,
    inventory,
    ownership: dict[str, Any],
) -> dict[str, Any]:
    result_ownership = dict(ownership)
    if replacing:
        if inventory.plugin and ownership["plugin"]:
            do, undo = manager.plugin_remove()
            tx.external(do, undo, manager.run)
        if inventory.marketplace and ownership["marketplace"]:
            do, undo = manager.marketplace_remove(old_version=old_version)
            tx.external(do, undo, manager.run)
        inventory = manager.inventory()
    if not inventory.marketplace:
        do, undo = manager.marketplace_add(version=new_version)
        tx.external(do, undo, manager.run)
    if inventory.plugin and not inventory.plugin_enabled and not replacing:
        if not ownership["plugin"]:
            raise InstallerError(f"{manager.host}の既存pluginはKiseki DA所有ではなくdisabledです。自動変更しません。")
        do, undo = manager.plugin_remove()
        tx.external(do, undo, manager.run)
        inventory = manager.inventory()
    if not inventory.plugin or not inventory.plugin_enabled or replacing:
        do, undo = manager.plugin_add()
        installed = tx.external(do, undo, manager.run)
        installed_path = _manager_installed_path(installed)
        if installed_path:
            result_ownership["installed_path"] = installed_path
    after = manager.inventory()
    if not after.marketplace:
        raise InstallerError(f"{manager.host}で{MARKETPLACE_ID} marketplaceの導入を確認できません。")
    if not after.plugin or not after.plugin_enabled:
        raise InstallerError(f"{manager.host}で{PLUGIN_ID}の導入を確認できません。")
    if after.plugin_version is not None and after.plugin_version != new_version:
        raise InstallerError(f"{manager.host}のplugin versionが不一致です: {after.plugin_version} != {new_version}")
    if not result_ownership.get("installed_path") and manager.host == "claude-code" and after.plugin_path:
        result_ownership["installed_path"] = after.plugin_path
    if not after.marketplace_fingerprint:
        raise InstallerError(f"{manager.host} marketplaceの供給元をinventoryから確認できません。")
    result_ownership["marketplace_fingerprint"] = after.marketplace_fingerprint
    installed_path = result_ownership.get("installed_path")
    if installed_path:
        _validate_installed_plugin(Path(str(installed_path)), manager.host, new_version)
    return result_ownership


def _manager_installed_path(result: subprocess.CompletedProcess[str]) -> str | None:
    try:
        value = json.loads(result.stdout)
    except (TypeError, ValueError):
        return None
    rows = [value]
    if isinstance(value, dict):
        rows.extend(item for item in (value.get("plugin"), value.get("result")) if isinstance(item, dict))
    for row in rows:
        if not isinstance(row, dict):
            continue
        for key in ("installedPath", "installPath", "installed_path", "install_path"):
            raw = row.get(key)
            if isinstance(raw, str) and raw and "\x00" not in raw:
                path = Path(raw).expanduser()
                if path.is_absolute() and path.resolve(strict=False).is_dir():
                    return str(path.resolve(strict=False))
    return None


def _validate_installed_plugin(path: Path, host: str, version: str) -> None:
    manifest_name = ".codex-plugin" if host == "codex" else ".claude-plugin"
    manifest = path / manifest_name / "plugin.json"
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise InstallerError(f"{host} installed plugin manifestを読めません: {manifest}: {exc}") from None
    if not isinstance(data, dict) or data.get("version") != version:
        raise InstallerError(f"{host} installed plugin versionが不一致です: {manifest}")
    if not (path / "scripts" / "hook_entry.py").is_file():
        raise InstallerError(f"{host} installed plugin hook launcherがありません: {path}")
    hook = path / "hooks" / ("hooks.json" if host == "codex" else "claude-code.json")
    try:
        hook_data = json.loads(hook.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise InstallerError(f"{host} installed hook定義を読めません: {hook}: {exc}") from None
    if not isinstance(hook_data, dict) or not isinstance(hook_data.get("hooks"), dict):
        raise InstallerError(f"{host} installed hook定義の形式が不正です: {hook}")


def _inventory_summary(inventory) -> dict[str, Any]:
    return {
        "marketplace": bool(inventory.marketplace),
        "plugin": bool(inventory.plugin),
        "plugin_enabled": bool(inventory.plugin_enabled),
        "plugin_version": inventory.plugin_version,
        "plugin_path": inventory.plugin_path,
        "marketplace_fingerprint": inventory.marketplace_fingerprint,
    }


def _install_action_plan(inventory, ownership: dict[str, Any], replacing: bool) -> list[str]:
    actions: list[str] = []
    if replacing and inventory.plugin and ownership.get("plugin"):
        actions.append("owned pluginを削除して再導入")
    elif inventory.plugin and not inventory.plugin_enabled:
        actions.append("disabled pluginを再導入")
    elif not inventory.plugin:
        actions.append("pluginを導入")
    else:
        actions.append("既存pluginをversion/有効性検証")
    if replacing and inventory.marketplace and ownership.get("marketplace"):
        actions.append("owned marketplaceを削除してtag固定で再登録")
    elif not inventory.marketplace:
        actions.append("marketplaceをtag固定で登録")
    else:
        actions.append("既存marketplaceを保持")
    return actions


def _host_ownership(
    old: dict[str, Any], previous_hosts: list[str], host: str, inventory, new_version: str,
) -> dict[str, Any]:
    previous = old.get("host_ownership")
    record = previous.get(host) if isinstance(previous, dict) else None
    if host in previous_hosts:
        # Metadata predating this ownership field was created only by the local
        # prerelease installer and is safely treated as installer-owned.
        marketplace_owned = bool(record.get("marketplace", True)) if isinstance(record, dict) else True
        plugin_owned = bool(record.get("plugin", True)) if isinstance(record, dict) else True
        if marketplace_owned and inventory.marketplace:
            recorded_source = record.get("marketplace_fingerprint") if isinstance(record, dict) else None
            if not recorded_source or recorded_source != inventory.marketplace_fingerprint:
                raise InstallerError(
                    f"{host} marketplaceの供給元/refが導入時記録と一致しません。自動変更しません。"
                )
    else:
        if inventory.marketplace or inventory.plugin:
            raise InstallerError(
                f"{host}に同名の既存marketplace/pluginがあります。供給元を自動採用しないため、"
                "native plugin managerで確認・削除してから再実行してください。"
            )
        marketplace_owned = not inventory.marketplace
        plugin_owned = not inventory.plugin
    if inventory.plugin and not inventory.marketplace:
        raise InstallerError(f"{host}のplugin inventoryが不整合です。既存pluginをnative managerで確認してください。")
    if marketplace_owned and inventory.plugin and not plugin_owned:
        raise InstallerError(f"{host}の既存pluginを保持したままmarketplaceだけを所有できません。")
    if inventory.plugin and not plugin_owned:
        if not inventory.plugin_enabled:
            raise InstallerError(f"{host}の既存pluginはdisabledです。自動で採用・変更しません。")
        if inventory.plugin_version != new_version:
            found = inventory.plugin_version or "不明"
            raise InstallerError(
                f"{host}の既存pluginは利用者管理です。version {found}を自動更新しません（必要: {new_version}）。"
            )
    installed_path = record.get("installed_path") if isinstance(record, dict) else None
    if not installed_path and host == "claude-code":
        installed_path = inventory.plugin_path
    if inventory.plugin and not plugin_owned and not installed_path:
        raise InstallerError(
            f"{host}の既存pluginは実installed pathを確認できないため自動採用しません。"
        )
    result = {
        "marketplace": marketplace_owned,
        "plugin": plugin_owned,
        "inventory_before": _inventory_summary(inventory),
    }
    if installed_path:
        result["installed_path"] = str(installed_path)
    if isinstance(record, dict) and record.get("marketplace_fingerprint"):
        result["marketplace_fingerprint"] = record["marketplace_fingerprint"]
    return result


def _hook_python(host: str) -> list[str]:
    if host == "claude-code":
        return [sys.executable]
    if os.name == "nt":
        launcher = shutil.which("py")
        return [launcher, "-3"] if launcher else []
    launcher = shutil.which("python3")
    return [launcher] if launcher else []


def _smoke_installed_plugins(host_ownership: dict[str, dict[str, Any]], version: str) -> None:
    """Exercise all five wrapper routes from the manager-installed plugin root."""
    with tempfile.TemporaryDirectory(prefix="kiseki-da-installed-hook-smoke-") as raw:
        base = Path(raw)
        for host, ownership in host_ownership.items():
            installed = ownership.get("installed_path")
            if not isinstance(installed, str):
                raise InstallerError(f"{host}のinstalled plugin pathを検証できません。")
            plugin = Path(installed)
            _validate_installed_plugin(plugin, host, version)
            state = base / host / "state"
            work = base / host / "workspace"
            work.mkdir(parents=True)
            env = os.environ.copy()
            env["KISEKI_DA_HOME"] = str(state)
            env["PLUGIN_ROOT"] = str(plugin)
            env["CLAUDE_PLUGIN_ROOT"] = str(plugin)
            python = _hook_python(host)
            if not python:
                raise InstallerError(f"{host} hookのPythonを解決できません。")
            cli = plugin / "core" / "ctx" / "cli.py"
            init = subprocess.run([*python, str(cli), "init"], capture_output=True, text=True,
                                  encoding="utf-8", errors="replace", env=env, check=False)
            if init.returncode != 0:
                raise InstallerError(f"{host} installed runtime init smokeに失敗しました。")
            cases = (
                ("session-start", {"hook_event_name": "SessionStart", "source": "startup"}, "Kiseki DA"),
                ("pre-tool", {"hook_event_name": "PreToolUse", "tool_name": "Bash",
                              "tool_input": {"command": "rm -rf /"}}, "deny"),
                ("post-tool", {"hook_event_name": "PostToolUse", "tool_name": "Bash",
                               "tool_input": {"command": "python -V"},
                               "tool_response": {"exit_code": 0, "stdout": "Python"}}, None),
                ("stop", {"hook_event_name": "Stop", "stop_hook_active": False}, None),
                ("session-end", {"hook_event_name": "SessionEnd", "reason": "install-smoke"}, None),
            )
            for event, fields, expected in cases:
                payload = {"session_id": f"installed-smoke-{host}", "cwd": str(work), **fields}
                result = subprocess.run(
                    [*python, str(plugin / "scripts" / "hook_entry.py"), event, host],
                    input=json.dumps(payload), capture_output=True, text=True,
                    encoding="utf-8", errors="replace", env=env, check=False,
                )
                if result.returncode != 0 or (expected and expected not in result.stdout):
                    detail = (result.stderr or result.stdout or f"exit {result.returncode}").strip()
                    raise InstallerError(f"{host} installed hook smoke ({event})に失敗しました: {detail}")
            event_types = set()
            for line in (state / "events.jsonl").read_text(encoding="utf-8").splitlines():
                try:
                    row = json.loads(line)
                except ValueError as exc:
                    raise InstallerError(f"{host} installed hook smokeのevent JSONが不正です: {exc}") from None
                if isinstance(row, dict) and isinstance(row.get("type"), str):
                    event_types.add(row["type"])
            for event_type in ("session_start", "guard", "tool_call", "session_end"):
                if event_type not in event_types:
                    raise InstallerError(f"{host} installed hook smokeに{event_type}記録がありません。")


def install(
    *,
    hosts: list[str],
    scope: str,
    project: Path | None,
    answers: dict[str, Any],
    yes: bool,
    dry_run: bool,
    source: Path = SOURCE_ROOT,
    update_mode: bool = False,
    host_security: str = "preserve",
    import_legacy: bool = False,
    allow_host_probes: bool = False,
) -> tuple[int, dict[str, Any]]:
    home = kiseki_home()
    _validate_platform_home(home)
    hosts = expand_hosts(hosts)
    if scope not in {"user", "project"}:
        raise InstallerError("scopeはuserまたはprojectです。")
    if host_security not in {"preserve", "recommended"}:
        raise InstallerError("host securityはpreserveまたはrecommendedです。")
    old = _metadata(home)
    if scope == "project" and project is not None:
        project = project.expanduser().resolve()
        if not project.is_dir():
            raise InstallerError(f"project directoryがありません: {project}")
    elif scope == "project" and not old.get("installed"):
        project = Path.cwd().resolve()
    source = source.resolve()
    source_info = preflight_source(source, hosts)
    answers = _validate_setup_answers(source, answers)
    model_preview = _preview_request(answers, hosts)
    legacy_home = _legacy_home()
    if import_legacy and legacy_home is None:
        raise InstallerError("importできる旧PA_HOME/~/.paがありません。")
    if import_legacy and any((home / name).exists() for name in
                             ("profile.toml", "events.jsonl", "candidates.jsonl", "tasks")):
        raise InstallerError("KISEKI_DA_HOMEに既存状態があるため旧状態を自動統合できません。")
    old_version = str(old.get("version")) if old.get("version") else None
    new_version = source_info["version"]
    replacing = bool(update_mode or (old_version and old_version != new_version))
    previous_hosts = [h for h in old.get("hosts", []) if h in HOSTS]
    location_pointer = _location_pointer_plan(home, old)
    base_plan = {
        "action": "update" if update_mode else "install",
        "home": str(home),
        "version": new_version,
        "hosts": hosts,
        "scope": scope,
        "project": str(project) if project else None,
        "legacy_detected": legacy_home is not None,
        "legacy_adapters": _legacy_adapter_paths(),
        "legacy_import": str(legacy_home) if import_legacy and legacy_home else None,
        "writes": [str(home / "runtime" / new_version), str(home / "current.json"), str(home / "install.json"),
                   str(home / "bin"), str(location_pointer["path"])],
        "setup_answers": {key: answers[key] for key in ("identity", "persona") if key in answers},
        "model_preview": model_preview,
        "security_settings": host_security,
        "security_changes": host_security_mod.preview(hosts) if host_security == "recommended" else [],
        "limitations": (["Codex Appのproject scopeはv0.1.0-beta.1ではLocal環境限定です。管理Worktree/Cloudではactivateしません。"]
                        if scope == "project" and "codex" in hosts else []),
    }
    if dry_run and not allow_host_probes:
        return 0, {
            **base_plan,
            "host_preflight": {host: {"status": "deferred_to_execution"} for host in hosts},
            "plugin_inventory": {host: {"status": "deferred_to_execution"} for host in hosts},
            "note": "dry-runではhost CLI内部の書込も避けるためversion/feature/inventory probeを実行時まで延期します。",
        }

    managers = {host: HostManager(host) for host in hosts}
    host_info = {host: managers[host].preflight() for host in hosts}
    initial_inventories = {host: managers[host].inventory() for host in hosts}
    selected_ownership = {
        host: _host_ownership(old, previous_hosts, host, initial_inventories[host], new_version)
        for host in hosts
    }
    prior_security_records = dict(old.get("security_records", {})) if isinstance(old.get("security_records"), dict) else {}
    security_refresh_hosts = [host for host in hosts
                              if replacing and host in previous_hosts and host in prior_security_records]
    if security_refresh_hosts:
        host_security_mod.validate_restore(prior_security_records, security_refresh_hosts)
    plan = {
        **base_plan,
        "host_preflight": host_info,
        "plugin_inventory": {host: _inventory_summary(initial_inventories[host]) for host in hosts},
        "host_ownership": selected_ownership,
        "host_actions": {
            host: _install_action_plan(initial_inventories[host], selected_ownership[host], replacing)
            for host in hosts
        },
    }
    if dry_run:
        return 0, plan

    preview_results: list[dict] = []
    tx: Transaction | None = None
    try:
        tx = Transaction(home, plan["action"])
        if _metadata(home) != old:
            raise InstallerError("確認後にinstall metadataが変更されました。再度planを確認してください。")
        for host in hosts:
            if _inventory_summary(managers[host].inventory()) != _inventory_summary(initial_inventories[host]):
                raise InstallerError(f"確認後に{host} plugin inventoryが変更されました。再実行してください。")
        if host_security == "recommended" and host_security_mod.preview(hosts) != plan["security_changes"]:
            raise InstallerError("確認後にhost security設定が変更されました。再度差分を確認してください。")
        if model_preview["enabled"]:
            print("キャラクター設定を選択したモデル提供者へ送信してプレビューします。応答はKiseki DAのstateへ保存しません。")
            persona_candidate = answers.get("persona") if isinstance(answers.get("persona"), dict) else {}
            preview_results = _run_model_preview(source, persona_candidate, model_preview["hosts"])
            for host in hosts:
                if _inventory_summary(managers[host].inventory()) != _inventory_summary(initial_inventories[host]):
                    raise InstallerError(f"プレビュー中に{host} plugin inventoryが変更されました。再実行してください。")
            if host_security == "recommended" and host_security_mod.preview(hosts) != plan["security_changes"]:
                raise InstallerError("プレビュー中にhost security設定が変更されました。再度差分を確認してください。")
        if import_legacy and legacy_home is not None:
            _import_legacy(tx, legacy_home, home)
        runtime = home / "runtime" / new_version
        with tempfile.TemporaryDirectory(prefix="kiseki-da-runtime-") as raw:
            staged = Path(raw) / "runtime"
            _runtime_source(source, staged)
            tx.replace_tree(staged, runtime)
        launchers, launcher_records = _write_launchers(tx, home, runtime, old)
        tx.write_json(home / "current.json", {
            "schema": 1,
            "version": new_version,
            "runtime": str(runtime),
            "updated_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        }, mode=0o600)
        _configure_runtime(tx, runtime, home, answers=answers, yes=yes, scope=scope, project=project,
                           hosts=hosts)
        # Runtime setup and legacy import intentionally use their own atomic
        # writers. Bind their resulting hashes to this transaction before any
        # external manager work so rollback never overwrites a concurrent edit.
        tx.capture_applied()
        if "codex" in hosts:
            tx.remove(home / "install" / "codex-hook-trust.json")
        security_records = dict(prior_security_records)
        for host in hosts:
            tx.track_external_mutable(host_security_mod.config_path(host))
        for host in security_refresh_hosts:
            host_security_mod.restore(tx, security_records, host)
            # The next apply must capture the new post-manager file as its
            # original.  Preserve the old artifacts through Transaction so an
            # update failure can restore them.
            tx.remove(home / "security-backups" / host / "record.json")
            tx.remove(home / "security-backups" / host / "original")
            security_records.pop(host, None)
        for host in hosts:
            host_replacing = replacing and host in previous_hosts
            selected_ownership[host] = _manager_steps(
                tx,
                managers[host],
                replacing=host_replacing,
                old_version=old_version,
                new_version=new_version,
                inventory=initial_inventories[host],
                ownership=selected_ownership[host],
            )
        _smoke_installed_plugins(selected_ownership, new_version)
        # Native managers may update their settings files.  Apply the optional
        # security baseline only after they are finished so its ownership hash
        # describes the actual final file.
        security_apply_hosts = hosts if host_security == "recommended" else security_refresh_hosts
        if security_apply_hosts:
            for host in security_apply_hosts:
                security_records[host] = host_security_mod.apply(tx, home, host)
        pointer_record = _write_location_pointer(tx, location_pointer)
        combined_hosts = list(dict.fromkeys([*previous_hosts, *hosts]))
        prior_ownership = old.get("host_ownership") if isinstance(old.get("host_ownership"), dict) else {}
        host_ownership = {host: prior_ownership.get(host, {"marketplace": True, "plugin": True})
                          for host in previous_hosts if host not in hosts}
        host_ownership.update(selected_ownership)
        registry = read_json(home / "projects.json", {})
        live_scope = registry.get("mode", scope) if isinstance(registry, dict) else scope
        registry_rows = registry.get("projects", []) if isinstance(registry, dict) else []
        projects = [str(row["path"]) for row in registry_rows
                    if isinstance(row, dict) and isinstance(row.get("path"), str)]
        metadata = {
            "schema": 1,
            "installed": True,
            "product": PRODUCT,
            "version": new_version,
            "hosts": combined_hosts,
            "scope": live_scope,
            "projects": projects,
            "source": f"blackrabbit74/kiseki-da@v{new_version}",
            "security_settings": "recommended" if security_records else "preserve",
            "security_records": security_records,
            "installed_at": old.get("installed_at") or dt.datetime.now().astimezone().isoformat(timespec="seconds"),
            "updated_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
            "legacy_detected": plan["legacy_detected"],
            "launchers": launcher_records,
            "location_pointer": pointer_record,
            "host_ownership": host_ownership,
        }
        tx.write_json(home / "install.json", metadata, mode=0o600)
        if not (runtime / "VERSION").is_file() or (runtime / "VERSION").read_text(encoding="utf-8").strip() != new_version:
            raise InstallerError("runtime version検証に失敗しました。")
        _smoke_runtime(runtime, hosts)
        tx.commit(version=new_version, hosts=combined_hosts, launchers=[str(p) for p in launchers])
        return 0, {**plan, "transaction": tx.id, "launchers": [str(p) for p in launchers],
                   "status": "installed", "preview_results": preview_results}
    except KeyboardInterrupt as exc:
        if tx is not None:
            ok = tx.rollback(run_command, error=exc)
            if not ok:
                return 3, {**plan, "transaction": tx.id, "status": "rollback_incomplete",
                           "journal": str(tx.journal_path), "rollback_errors": tx.data.get("rollback_errors", [])}
        return 130, {**plan, "transaction": tx.id if tx else None, "status": "interrupted"}
    except BaseException as exc:  # noqa: BLE001 - operation must roll back any post-begin failure
        if tx is None:
            if isinstance(exc, InstallerError):
                raise
            raise InstallerError(f"install開始前に失敗しました: {type(exc).__name__}: {exc}") from None
        ok = tx.rollback(run_command, error=exc)
        return (2 if ok else 3), {
            **plan, "transaction": tx.id, "status": "rolled_back" if ok else "rollback_incomplete",
            "error": str(exc), "journal": str(tx.journal_path),
            "rollback_errors": tx.data.get("rollback_errors", []),
        }


def uninstall(
    *, hosts: list[str] | None, dry_run: bool, allow_host_probes: bool = False,
) -> tuple[int, dict[str, Any]]:
    home = kiseki_home()
    old = _metadata(home)
    if not old.get("installed"):
        raise InstallerError("Kiseki DAはインストールされていません。")
    installed_hosts = [h for h in old.get("hosts", []) if h in HOSTS]
    selected = installed_hosts if not hosts or "all" in hosts else expand_hosts(hosts)
    selected = [host for host in selected if host in installed_hosts]
    if not selected:
        raise InstallerError("指定hostにはKiseki DAがインストールされていません。")
    security_records = dict(old.get("security_records", {})) if isinstance(old.get("security_records"), dict) else {}
    ownership_records = old.get("host_ownership") if isinstance(old.get("host_ownership"), dict) else {}
    host_security_mod.validate_restore(security_records, selected)
    remaining = [host for host in installed_hosts if host not in selected]
    launcher_records = [item for item in old.get("launchers", []) if isinstance(item, dict)]
    owned_pointer: Path | None = None
    if not remaining:
        for item in launcher_records:
            path = Path(str(item.get("path", "")))
            if (item.get("kind") != "file" or path.is_symlink() or not path.is_file()
                    or sha256_file(path) != item.get("sha256")):
                raise InstallerError(f"launcherは導入後に変更されています。自動削除しません: {path}")
        owned_pointer = _validate_owned_pointer(old.get("location_pointer"))
    plan = {
        "action": "uninstall",
        "home": str(home),
        "hosts": selected,
        "remaining_hosts": remaining,
        "state_preserved": True,
        "host_preflight": {host: {"status": "deferred_to_execution"} for host in selected},
        "note": "dry-runではhost CLI内部の書込も避けるためversion/feature/inventory probeを実行時まで延期します。",
    }
    if dry_run and not allow_host_probes:
        return 0, plan
    managers = {host: HostManager(host) for host in selected}
    host_info = {host: managers[host].preflight() for host in selected}
    plan["host_preflight"] = host_info
    plan.pop("note", None)
    inventories = {host: managers[host].inventory() for host in selected}
    plan["plugin_inventory"] = {host: _inventory_summary(value) for host, value in inventories.items()}
    plan["host_actions"] = {}
    for host, inventory in inventories.items():
        ownership = ownership_records.get(host)
        if not isinstance(ownership, dict):
            ownership = {"marketplace": True, "plugin": True}
        if (inventory.marketplace and ownership.get("marketplace") is True
                and ownership.get("marketplace_fingerprint") != inventory.marketplace_fingerprint):
            raise InstallerError(f"{host} marketplaceの供給元/refが導入時記録と一致しません。自動削除しません。")
        actions = []
        actions.append("owned pluginを削除" if inventory.plugin and ownership.get("plugin") else "pluginを保持/対象なし")
        actions.append("owned marketplaceを削除" if inventory.marketplace and ownership.get("marketplace")
                       else "marketplaceを保持/対象なし")
        plan["host_actions"][host] = actions
    if dry_run:
        return 0, plan
    tx: Transaction | None = None
    try:
        tx = Transaction(home, "uninstall")
        if _metadata(home) != old:
            raise InstallerError("確認後にinstall metadataが変更されました。再度planを確認してください。")
        for host in selected:
            if _inventory_summary(managers[host].inventory()) != _inventory_summary(inventories[host]):
                raise InstallerError(f"確認後に{host} plugin inventoryが変更されました。再実行してください。")
        old_version = str(old.get("version", VERSION))
        for host in selected:
            manager = managers[host]
            ownership = ownership_records.get(host)
            if not isinstance(ownership, dict):
                ownership = {"marketplace": True, "plugin": True}
            tx.track_external_mutable(host_security_mod.config_path(host))
            # Restore the post-manager/pre-security snapshot first.  Claude's
            # plugin removal can then remove its own settings entry without a
            # later whole-file security restore reintroducing it.
            host_security_mod.restore(tx, security_records, host)
            inventory = inventories[host]
            if inventory.plugin and ownership.get("plugin") is True:
                do, undo = manager.plugin_remove()
                tx.external(do, undo, manager.run)
            if inventory.marketplace and ownership.get("marketplace") is True:
                do, undo = manager.marketplace_remove(old_version=old_version)
                tx.external(do, undo, manager.run)
            after = manager.inventory()
            if ownership.get("plugin") is True and after.plugin:
                raise InstallerError(f"{host} pluginの削除を確認できません。")
            if ownership.get("marketplace") is True and after.marketplace:
                raise InstallerError(f"{host} marketplaceの削除を確認できません。")
            if host in security_records:
                tx.remove(home / "security-backups" / host / "record.json")
                tx.remove(home / "security-backups" / host / "original")
            security_records.pop(host, None)
            if host == "codex":
                tx.remove(home / "install" / "codex-hook-trust.json")
        metadata = dict(old)
        metadata["hosts"] = remaining
        metadata["installed"] = bool(remaining)
        metadata["security_records"] = security_records
        metadata["security_settings"] = "recommended" if security_records else "preserve"
        metadata["host_ownership"] = {host: record for host, record in ownership_records.items()
                                      if host in remaining}
        metadata["updated_at"] = dt.datetime.now().astimezone().isoformat(timespec="seconds")
        tx.write_json(home / "install.json", metadata, mode=0o600)
        if not remaining:
            for item in launcher_records:
                path = Path(str(item.get("path", "")))
                if path.is_file():
                    tx.remove_external(path)
            if owned_pointer is not None and owned_pointer.is_file():
                tx.remove_external(owned_pointer)
            tx.remove(home / "current.json")
            tx.remove(home / "runtime")
            for name in ("kiseki-da", "kiseki-da.py", "kiseki-da.cmd"):
                tx.remove(home / "bin" / name)
        tx.commit(hosts=remaining, state_preserved=True)
        return 0, {**plan, "transaction": tx.id, "status": "uninstalled" if not remaining else "partially_uninstalled"}
    except KeyboardInterrupt as exc:
        if tx is not None:
            ok = tx.rollback(run_command, error=exc)
            if not ok:
                return 3, {**plan, "transaction": tx.id, "status": "rollback_incomplete",
                           "journal": str(tx.journal_path), "rollback_errors": tx.data.get("rollback_errors", [])}
        return 130, {**plan, "transaction": tx.id if tx else None, "status": "interrupted"}
    except BaseException as exc:  # noqa: BLE001
        if tx is None:
            if isinstance(exc, InstallerError):
                raise
            raise InstallerError(str(exc)) from None
        ok = tx.rollback(run_command, error=exc)
        return (2 if ok else 3), {
            **plan, "transaction": tx.id, "status": "rolled_back" if ok else "rollback_incomplete",
            "error": str(exc), "journal": str(tx.journal_path),
            "rollback_errors": tx.data.get("rollback_errors", []),
        }


def doctor() -> tuple[int, dict[str, Any]]:
    home = kiseki_home()
    metadata = _metadata(home)
    checks: list[dict[str, Any]] = []
    smoke_targets: dict[str, dict[str, Any]] = {}

    def add(name: str, status: str, detail: str) -> None:
        checks.append({"name": name, "status": status, "detail": detail})

    try:
        _validate_platform_home(home)
    except InstallerError as exc:
        add("state-permissions", "error", str(exc))
    else:
        add("state-permissions", "ok", "state root/parent access policy")

    if platform.system() == "Linux" and (os.environ.get("WSL_DISTRO_NAME") or "microsoft" in platform.release().casefold()):
        parts = home.parts
        if len(parts) >= 3 and parts[1] == "mnt" and len(parts[2]) == 1:
            add("wsl-home", "error", "WSLでは/mnt/<drive>配下をKISEKI_DA_HOMEにできません")
    pointer = read_json(home / "current.json", {})
    if not metadata.get("installed") or not isinstance(pointer, dict) or not pointer.get("runtime"):
        add("installation", "error", "インストールされていません")
    else:
        runtime = Path(pointer["runtime"])
        version_file = runtime / "VERSION"
        if runtime.is_dir() and version_file.is_file() and version_file.read_text(encoding="utf-8").strip() == metadata.get("version"):
            add("runtime", "ok", str(metadata.get("version")))
        else:
            add("runtime", "error", "current pointerまたはversionが不整合です")
        for name in ("kiseki-da.py", "kiseki-da", "kiseki-da.cmd"):
            launcher = home / "bin" / name
            add(f"launcher:{name}", "ok" if launcher.is_file() and not launcher.is_symlink() else "error", str(launcher))
        for item in metadata.get("launchers", []):
            if not isinstance(item, dict):
                continue
            path = Path(str(item.get("path", "")))
            valid = (item.get("kind") == "file" and path.is_file() and not path.is_symlink()
                     and sha256_file(path) == item.get("sha256"))
            add("launcher:PATH", "ok" if valid and shutil.which("kiseki-da") else "notice",
                str(path) if valid else f"不整合: {path}")
        pointer_record = metadata.get("location_pointer")
        pointer_ok = False
        pointer_detail = "記録がありません"
        if isinstance(pointer_record, dict) and isinstance(pointer_record.get("path"), str):
            location = Path(pointer_record["path"])
            try:
                private_mode = os.name == "nt" or not bool(location.stat().st_mode & 0o022)
                pointer_ok = (
                    location == kiseki_pointer_path()
                    and location.is_file() and not location.is_symlink()
                    and sha256_file(location) == pointer_record.get("sha256")
                    and location.read_text(encoding="utf-8") == location_pointer_text(home)
                    and private_mode
                )
                pointer_detail = str(location) if pointer_ok else f"path/hash/content/mode不整合: {location}"
            except OSError as exc:
                pointer_detail = f"読取失敗: {location}: {exc}"
        add("location-pointer", "ok" if pointer_ok else "error", pointer_detail)
    legacy = bool(os.environ.get("PA_HOME") or (Path.home() / ".pa").exists())
    add("legacy-pa", "notice" if legacy else "ok", "検出しました（自動importしません）" if legacy else "未検出")
    active = active_transactions(home)
    add("transactions", "error" if active else "ok", ", ".join(active) if active else "未完了なし")
    for host in [h for h in metadata.get("hosts", []) if h in HOSTS]:
        try:
            manager = HostManager(host)
            info = manager.preflight()
            inventory = manager.inventory()
            ownerships = metadata.get("host_ownership") if isinstance(metadata.get("host_ownership"), dict) else {}
            ownership = ownerships.get(host) if isinstance(ownerships.get(host), dict) else {}
            installed_path = ownership.get("installed_path")
            version_ok = inventory.plugin_version in {None, metadata.get("version")}
            marketplace_ok = (ownership.get("marketplace_fingerprint") == inventory.marketplace_fingerprint
                              if ownership.get("marketplace") is True else True)
            host_ok = inventory.plugin and inventory.plugin_enabled and version_ok and marketplace_ok
            plugin_detail = info["version"] + (f" ({installed_path})" if installed_path else "")
            if inventory.plugin and not inventory.plugin_enabled:
                plugin_detail += " / plugin disabled"
            if not version_ok:
                plugin_detail += f" / plugin {inventory.plugin_version} != {metadata.get('version')}"
            if not marketplace_ok:
                plugin_detail += " / marketplace source/ref mismatch"
            add(f"host:{host}", "ok" if host_ok else "error", plugin_detail)
            if isinstance(installed_path, str):
                try:
                    _validate_installed_plugin(Path(installed_path), host, str(metadata.get("version")))
                except InstallerError as exc:
                    add(f"installed-plugin:{host}", "error", str(exc))
                else:
                    add(f"installed-plugin:{host}", "ok", installed_path)
                    smoke_targets[host] = {"installed_path": installed_path}
            else:
                add(f"installed-plugin:{host}", "error", "記録済みinstalled pathがありません")
            if host == "codex":
                attestation = read_json(home / "install" / "codex-hook-trust.json", {})
                if not isinstance(installed_path, str):
                    add("codex-hook-trust", "pending_activation",
                        "installed plugin pathをinventoryから確認できません")
                else:
                    plugin_path = Path(installed_path)
                    hook_path = plugin_path / "hooks" / "hooks.json"
                    try:
                        current_hash = hashlib.sha256(hook_path.read_bytes()).hexdigest()
                    except OSError as exc:
                        add("codex-hook-trust", "error", f"installed hook定義を読めません: {exc}")
                    else:
                        trusted = (isinstance(attestation, dict)
                                   and attestation.get("version") == metadata.get("version")
                                   and attestation.get("plugin_path") == str(plugin_path)
                                   and attestation.get("hook_sha256") == current_hash)
                        add("codex-hook-trust", "ok" if trusted else "pending_activation",
                            "未確認: Codexの/hooksでtrustしてください" if not trusted else "確認済み")
        except InstallerError as exc:
            add(f"host:{host}", "error", str(exc))
    if smoke_targets:
        try:
            _smoke_installed_plugins(smoke_targets, str(metadata.get("version")))
        except InstallerError as exc:
            add("installed-hook-smoke", "error", str(exc))
        else:
            add("installed-hook-smoke", "ok", "5 hook routes / disposable state")
    statuses = {item["status"] for item in checks}
    overall = "error" if "error" in statuses else ("pending_activation" if "pending_activation" in statuses else "healthy")
    return (0 if overall == "healthy" else 1), {
        "product": PRODUCT,
        "home": str(home),
        "status": overall,
        "version": metadata.get("version"),
        "checks": checks,
    }


def attest_codex_trust() -> dict[str, Any]:
    """Record an explicit user attestation for the exact installed Codex hook definition."""
    home = kiseki_home()
    metadata = _metadata(home)
    if "codex" not in metadata.get("hosts", []):
        raise InstallerError("Codex pluginがインストールされていません。")
    manager = HostManager("codex")
    manager.preflight()
    inventory = manager.inventory()
    if not inventory.plugin or not inventory.plugin_enabled:
        raise InstallerError("Codex pluginが有効なinstalled状態ではありません。")
    ownerships = metadata.get("host_ownership") if isinstance(metadata.get("host_ownership"), dict) else {}
    ownership = ownerships.get("codex") if isinstance(ownerships.get("codex"), dict) else {}
    installed_path = ownership.get("installed_path")
    if not isinstance(installed_path, str):
        raise InstallerError("Codexの記録済みinstalled plugin pathを確認できません。")
    plugin_path = Path(installed_path)
    _validate_installed_plugin(plugin_path, "codex", str(metadata.get("version")))
    hook_path = plugin_path / "hooks" / "hooks.json"
    try:
        digest = hashlib.sha256(hook_path.read_bytes()).hexdigest()
    except OSError as exc:
        raise InstallerError(f"Codex hook定義を読めません: {exc}") from None
    record = {
        "schema": 1,
        "version": metadata.get("version"),
        "plugin_path": str(plugin_path),
        "hook_sha256": digest,
        "attested_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "statement": "利用者がCodex /hooksで現在のKiseki DA hookを確認しtrustした",
    }
    tx: Transaction | None = None
    try:
        tx = Transaction(home, "config:codex-hook-trust", preserve_user_state_on_manual=False)
        tx.write_json(home / "install" / "codex-hook-trust.json", record, mode=0o600)
        tx.commit(version=metadata.get("version"), plugin_path=str(plugin_path))
        return {**record, "transaction": tx.id}
    except BaseException as exc:  # noqa: BLE001
        if tx is None:
            raise InstallerError(str(exc)) from None
        ok = tx.rollback(run_command, error=exc)
        suffix = "rollback済み" if ok else "rollback不完全"
        raise InstallerError(f"Codex trust記録に失敗しました（{suffix}）: {exc}") from None


def rollback(transaction_id: str) -> tuple[int, dict[str, Any]]:
    home = kiseki_home()
    txid, ok, errors = rollback_saved(home, transaction_id, run_command)
    return (0 if ok else 3), {
        "transaction": txid, "status": "rolled_back" if ok else "rollback_incomplete",
        "errors": errors, "journal": str(kiseki_home() / "transactions" / txid / "journal.json"),
    }


def installed_runtime() -> Path:
    home = kiseki_home()
    pointer = read_json(home / "current.json", {})
    if not isinstance(pointer, dict) or not pointer.get("runtime"):
        raise InstallerError("Kiseki DA runtimeがありません。先にinstallを実行してください。")
    runtime = Path(pointer["runtime"]).resolve()
    if not runtime.is_dir():
        raise InstallerError(f"Kiseki DA runtimeがありません: {runtime}")
    return runtime


def _runtime_config_mutation(argv: list[str]) -> bool:
    if not argv:
        return False
    if argv[0] == "setup":
        return True
    if argv[0] == "persona" and len(argv) > 1 and argv[1] in {"edit", "reset"}:
        return True
    if argv[0] == "session" and len(argv) > 1 and argv[1] == "clear":
        return True
    return argv[0] == "project" and len(argv) > 1 and argv[1] in {"add", "remove"}


def runtime_dispatch(argv: list[str]) -> int:
    runtime = installed_runtime()
    home = kiseki_home()
    plugin = runtime / "plugins" / "kiseki-da"
    sys.path.insert(0, str(plugin))
    os.environ["KISEKI_DA_HOME"] = str(home)
    from core.ctx.cli import main as runtime_main
    if not _runtime_config_mutation(argv):
        return int(runtime_main(argv))

    from core.ctx.scope import load_registry, resolve_scope

    tx: Transaction | None = None
    try:
        tx = Transaction(home, "config:" + ":".join(argv[:2]), preserve_user_state_on_manual=False)
        before_registry = load_registry(home)
        before_ids = {str(row.get("id")) for row in before_registry.get("projects", []) if isinstance(row, dict)}
        resolved = resolve_scope(home, Path.cwd())
        targets = [home / "profile.toml", home / "snapshots", home / "projects.json", home / "install.json"]
        if resolved.state_home is not None:
            targets.append(resolved.state_home / "session")
        if resolved.state_home is not None and resolved.state_home != home:
            targets.extend((resolved.state_home / "profile.toml", resolved.state_home / "snapshots"))
        for target in targets:
            tx.backup(target)
        code = int(runtime_main(argv) or 0)
        if code != 0:
            ok = tx.rollback(run_command, error=f"runtime command exited {code}")
            return code if ok and code in {1, 130} else (2 if ok else 3)
        after_registry = load_registry(home)
        for row in after_registry.get("projects", []):
            if isinstance(row, dict) and str(row.get("id")) not in before_ids:
                tx.track_created(home / "projects" / str(row["id"]))
        metadata = _metadata(home)
        if metadata.get("installed"):
            metadata["scope"] = after_registry.get("mode", metadata.get("scope", "user"))
            metadata["projects"] = [str(row["path"]) for row in after_registry.get("projects", [])
                                    if isinstance(row, dict) and isinstance(row.get("path"), str)]
            metadata["updated_at"] = dt.datetime.now().astimezone().isoformat(timespec="seconds")
            tx.write_json(home / "install.json", metadata, mode=0o600)
        tx.capture_applied()
        tx.commit(command=argv[:2])
        print(f"transaction: {tx.id}")
        return 0
    except KeyboardInterrupt as exc:
        if tx is not None:
            tx.rollback(run_command, error=exc)
        return 130
    except BaseException as exc:  # noqa: BLE001 - configuration changes must roll back
        if tx is None:
            raise InstallerError(str(exc)) from None
        ok = tx.rollback(run_command, error=exc)
        print(f"設定変更に失敗しました: {exc}", file=sys.stderr)
        return 2 if ok else 3


def describe_plan(data: dict[str, Any]) -> str:
    lines = [f"操作: {data.get('action')}", f"KISEKI_DA_HOME: {data.get('home')}"]
    if data.get("version"):
        lines.append(f"version: {data['version']}")
    if data.get("hosts") is not None:
        lines.append("host: " + ", ".join(data.get("hosts", [])))
    if data.get("scope"):
        lines.append(f"scope: {data['scope']}")
    if data.get("project"):
        lines.append(f"project: {data['project']}")
    host_preflight = data.get("host_preflight")
    inventories = data.get("plugin_inventory")
    ownerships = data.get("host_ownership")
    actions = data.get("host_actions")
    if isinstance(host_preflight, dict):
        lines.append("host事前検査・plugin inventory:")
        for host in data.get("hosts", []):
            info = host_preflight.get(host, {})
            inventory = inventories.get(host, {}) if isinstance(inventories, dict) else {}
            ownership = ownerships.get(host, {}) if isinstance(ownerships, dict) else {}
            detail = info.get("status") or f"version={info.get('version')} executable={info.get('executable')}"
            lines.append(f"  - {host}: {detail}")
            if inventory:
                lines.append("    inventory: " + json.dumps(inventory, ensure_ascii=False, sort_keys=True))
            if ownership:
                lines.append("    installer ownership: " + json.dumps(
                    {key: ownership.get(key) for key in ("marketplace", "plugin", "installed_path") if key in ownership},
                    ensure_ascii=False, sort_keys=True,
                ))
            if isinstance(actions, dict):
                for action in actions.get(host, []):
                    lines.append(f"    予定: {action}")
    setup_answers = data.get("setup_answers")
    if isinstance(setup_answers, dict):
        lines.append("保存する初期設定候補:")
        identity = setup_answers.get("identity")
        persona = setup_answers.get("persona")
        lines.append("  利用者情報: " + json.dumps(identity if isinstance(identity, dict) else {}, ensure_ascii=False))
        lines.append("  キャラクター: " + json.dumps(persona if isinstance(persona, dict) else {}, ensure_ascii=False))
    if "model_preview" in data:
        model_preview = data.get("model_preview")
        if isinstance(model_preview, dict) and model_preview.get("enabled"):
            lines.append("モデルプレビュー: 実行する（設定候補をモデル提供者へ送信、stateには保存しない）")
            lines.append("  対象host: " + ", ".join(model_preview.get("hosts", [])))
        else:
            lines.append("モデルプレビュー: 実行しない")
    if "security_settings" in data:
        if data.get("security_settings") == "recommended":
            lines.append("host security設定: 推奨値を適用（全体バックアップ・差分hash検証あり）")
            for item in data.get("security_changes", []):
                lines.append(f"  - {item['host']}: {item['path']} ({item['before'][:12]} -> {item['after'][:12]})")
                for change in item.get("changes", []):
                    if "add" in change:
                        lines.append(f"    {change['key']}: 追加 {json.dumps(change['add'], ensure_ascii=False)}")
                    else:
                        lines.append(f"    {change['key']}: {change.get('before')} -> {change.get('after')}")
        else:
            lines.append("host security設定: 変更しない")
    if data.get("legacy_detected") and not data.get("legacy_import"):
        lines.append("旧~/.paを検出: 自動importしない")
    if data.get("legacy_import"):
        lines.append(f"旧状態をcopyして移行: {data['legacy_import']}")
    if data.get("legacy_adapters"):
        lines.append("旧manual adapterを検出（自動編集しません。backup後の明示移行を推奨）:")
        lines.extend(f"  - {path}" for path in data["legacy_adapters"])
    if data.get("limitations"):
        lines.append("対応上の制限:")
        lines.extend(f"  - {item}" for item in data["limitations"])
    if data.get("writes"):
        lines.append("変更予定:")
        lines.extend(f"  - {path}" for path in data["writes"])
    if data.get("note"):
        lines.append(str(data["note"]))
    return "\n".join(lines)
