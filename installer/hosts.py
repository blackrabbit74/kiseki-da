"""Native Claude Code and Codex plugin-manager adapters."""
from __future__ import annotations

import json
import os
import platform
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from .constants import MARKETPLACE_ID, MARKETPLACE_REPO, MIN_VERSIONS, PLUGIN_ID, TAG
from .util import InstallerError, parse_version


def _codex_app_candidates() -> list[Path]:
    """Known local Mac app locations; never search the current project or launch a shell."""
    return [directory / app / "Contents" / "Resources" / "codex"
            for directory in (Path("/Applications"), Path.home() / "Applications")
            for app in ("ChatGPT.app", "Codex.app")]


def _executable(host: str) -> list[str]:
    key = "KISEKI_DA_CLAUDE_COMMAND" if host == "claude-code" else "KISEKI_DA_CODEX_COMMAND"
    configured = os.environ.get(key)
    if configured:
        values = shlex.split(configured, posix=os.name != "nt")
        if not values:
            raise InstallerError(f"{key} が空です。")
        return values
    command = "claude" if host == "claude-code" else "codex"
    resolved = shutil.which(command)
    if resolved:
        return [resolved]
    if host == "codex" and sys.platform == "darwin":
        for candidate in _codex_app_candidates():
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return [str(candidate)]
    return [command]


def run_command(argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
    timeout = int(os.environ.get("KISEKI_DA_HOST_TIMEOUT", "90"))
    values = list(map(str, argv))
    if os.name == "nt" and values and Path(values[0]).suffix.casefold() in {".cmd", ".bat"}:
        comspec = os.environ.get("COMSPEC", "cmd.exe")
        values = [comspec, "/d", "/s", "/c", subprocess.list2cmdline(values)]
    try:
        return subprocess.run(
            values,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            env=os.environ.copy(),
            check=False,
        )
    except FileNotFoundError:
        return subprocess.CompletedProcess(list(argv), 127, "", f"コマンドがありません: {argv[0]}")
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(list(argv), 124, "", f"{timeout}秒でタイムアウトしました")


def _decode_json(result: subprocess.CompletedProcess[str]) -> Any:
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except (TypeError, ValueError):
        return result.stdout


@dataclass(frozen=True)
class Inventory:
    marketplace: bool
    plugin: bool
    marketplace_raw: Any
    plugin_raw: Any
    plugin_enabled: bool = False
    plugin_version: str | None = None
    plugin_path: str | None = None
    marketplace_fingerprint: dict[str, Any] | None = None


def _require_rows(value: Any, key: str, label: str) -> list[dict]:
    if isinstance(value, list) and all(isinstance(item, dict) for item in value):
        return list(value)
    if (isinstance(value, dict) and isinstance(value.get(key), list)
            and all(isinstance(item, dict) for item in value[key])):
        return list(value[key])
    raise InstallerError(f"{label} inventoryのJSON形式を認識できません。")


def _marketplace_match(row: dict) -> bool:
    return row.get("name") == MARKETPLACE_ID or row.get("marketplaceName") == MARKETPLACE_ID


def _plugin_match(row: dict) -> bool:
    expected = f"{PLUGIN_ID}@{MARKETPLACE_ID}"
    plugin_id = row.get("pluginId") or row.get("id")
    if plugin_id == expected:
        return True
    return row.get("name") == PLUGIN_ID and row.get("marketplaceName") == MARKETPLACE_ID


def _installed_plugin_path(row: dict) -> str | None:
    """Extract only documented/path-shaped fields from the matched installed row.

    Do not recursively search arbitrary strings: marketplace paths and available
    plugin descriptions can also contain the plugin name but are not the loaded
    plugin directory.
    """
    candidates: list[object] = [
        row.get("installPath"), row.get("install_path"), row.get("pluginPath"),
        row.get("plugin_path"), row.get("path"),
    ]
    source = row.get("source")
    if isinstance(source, dict):
        candidates.extend((source.get("path"), source.get("installPath"), source.get("pluginPath")))
    for value in candidates:
        if not isinstance(value, str) or not value or "\x00" in value:
            continue
        path = Path(value).expanduser()
        if not path.is_absolute():
            continue
        resolved = path.resolve(strict=False)
        if resolved.is_dir():
            return str(resolved)
    return None


def _fingerprint(value: object) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    keys = ("source", "sourceType", "path", "url", "repo", "ref", "sha")
    result: dict[str, Any] = {}
    for key in keys:
        item = value.get(key)
        if isinstance(item, (str, int, bool)):
            result[key] = item
        elif isinstance(item, dict):
            nested = _fingerprint(item)
            if nested:
                result[key] = nested
    return result or None


def _claude_user_marketplace() -> dict[str, Any] | None:
    """Return the exact user-scope source, excluding same-name project rows."""
    root = Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude")).expanduser()
    try:
        data = json.loads((root / "settings.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    extra = data.get("extraKnownMarketplaces") if isinstance(data, dict) else None
    entry = extra.get(MARKETPLACE_ID) if isinstance(extra, dict) else None
    return _fingerprint(entry.get("source")) if isinstance(entry, dict) else None


class HostManager:
    def __init__(self, host: str):
        if host not in MIN_VERSIONS:
            raise InstallerError(f"未対応hostです: {host}")
        self.host = host
        self.base = _executable(host)

    def argv(self, *parts: str) -> list[str]:
        return [*self.base, *parts]

    def run(self, argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
        return run_command(argv)

    def preflight(self) -> dict[str, Any]:
        executable = self.base[0]
        resolved_text = str(Path(executable).resolve()) if Path(executable).is_file() else shutil.which(executable)
        if not resolved_text:
            if self.host == "codex" and sys.platform == "darwin" and not os.environ.get("KISEKI_DA_CODEX_COMMAND"):
                raise InstallerError(
                    "CodexのCLIが見つかりません。/Applications または ~/Applications の"
                    "ChatGPT.app / Codex.appにも実行ファイルがありません。アプリを導入するか、"
                    "KISEKI_DA_CODEX_COMMANDにCLIのパスを指定してください。"
                    "手順: docs/INSTALLATION.md「Codexアプリだけを使っている場合」"
                )
            raise InstallerError(f"{self.host} のCLIが見つかりません: {executable}")
        resolved = Path(resolved_text).resolve(strict=False)
        is_wsl = bool(os.environ.get("WSL_DISTRO_NAME") or "microsoft" in platform.release().casefold())
        if is_wsl and (resolved.suffix.casefold() in {".exe", ".cmd", ".bat"}
                       or (len(resolved.parts) >= 3 and resolved.parts[1] == "mnt")):
            raise InstallerError(f"WSLではWindows側のhost CLIを使用できません: {resolved}")
        if os.name == "nt" and self.host == "codex":
            launcher = shutil.which("py")
            if not launcher:
                raise InstallerError("Windows nativeのCodexにはPython Launcher（py -3）が必要です。")
            probe = run_command([launcher, "-3", "-c", "import sys; print('.'.join(map(str, sys.version_info[:3])))"])
            python_version = parse_version(probe.stdout)
            if (probe.returncode != 0 or python_version is None
                    or not (3, 11, 0) <= python_version < (3, 15, 0)):
                raise InstallerError("py -3が対応Python 3.11〜3.14を起動できません。")
        elif os.name != "nt" and self.host == "codex":
            launcher = shutil.which("python3")
            if not launcher:
                raise InstallerError("Codex hookの実行にpython3が必要です。")
            probe = run_command([launcher, "-c", "import sys; print('.'.join(map(str, sys.version_info[:3])))"])
            python_version = parse_version(probe.stdout)
            if (probe.returncode != 0 or python_version is None
                    or not (3, 11, 0) <= python_version < (3, 15, 0)):
                raise InstallerError("python3が対応Python 3.11〜3.14を起動できません。")
        version_result = self.run(self.argv("--version"))
        if version_result.returncode != 0:
            raise InstallerError(f"{self.host} のversion確認に失敗しました。")
        version = parse_version(version_result.stdout + " " + version_result.stderr)
        if version is None:
            raise InstallerError(f"{self.host} のversionを判定できません: {version_result.stdout.strip()}")
        if version < MIN_VERSIONS[self.host]:
            minimum = ".".join(map(str, MIN_VERSIONS[self.host]))
            raise InstallerError(f"{self.host} {minimum}以上が必要です（検出: {'.'.join(map(str, version))}）。")
        help_result = self.run(self.argv("plugin", "--help"))
        help_text = (help_result.stdout + help_result.stderr).casefold()
        required = ("marketplace", "install") if self.host == "claude-code" else ("marketplace", "add")
        if help_result.returncode != 0 or not all(word in help_text for word in required):
            raise InstallerError(f"{self.host} のplugin managerに必要な機能がありません。")
        return {"version": ".".join(map(str, version)), "executable": str(resolved), "features": list(required)}

    def inventory(self) -> Inventory:
        if self.host == "claude-code":
            market_cmd = self.argv("plugin", "marketplace", "list", "--json")
            plugin_cmd = self.argv("plugin", "list", "--json")
        else:
            market_cmd = self.argv("plugin", "marketplace", "list", "--json")
            plugin_cmd = self.argv("plugin", "list", "--json")
        market_result = self.run(market_cmd)
        plugin_result = self.run(plugin_cmd)
        if market_result.returncode != 0:
            detail = (market_result.stderr or market_result.stdout or str(market_result.returncode)).strip()
            raise InstallerError(f"{self.host} marketplace inventoryに失敗しました: {detail}")
        if plugin_result.returncode != 0:
            detail = (plugin_result.stderr or plugin_result.stdout or str(plugin_result.returncode)).strip()
            raise InstallerError(f"{self.host} plugin inventoryに失敗しました: {detail}")
        market_raw = _decode_json(market_result)
        plugin_raw = _decode_json(plugin_result)
        marketplaces = _require_rows(market_raw, "marketplaces", f"{self.host} marketplace")
        installed = _require_rows(plugin_raw, "installed", f"{self.host} plugin")
        market = next((row for row in marketplaces if _marketplace_match(row)), None)
        claude_source = _claude_user_marketplace() if self.host == "claude-code" else None
        marketplace_present = claude_source is not None if self.host == "claude-code" else market is not None
        marketplace_fingerprint = (claude_source if self.host == "claude-code" else
                                   _fingerprint(market.get("marketplaceSource")) if market else None)
        plugin = next((row for row in installed if _plugin_match(row)
                       and (self.host != "claude-code" or row.get("scope", "user") == "user")
                       and row.get("installed", True) is not False), None)
        return Inventory(
            marketplace=marketplace_present,
            plugin=plugin is not None,
            marketplace_raw=market_raw,
            plugin_raw=plugin_raw,
            plugin_enabled=bool(plugin and plugin.get("enabled", True) is not False),
            plugin_version=str(plugin.get("version")) if plugin and plugin.get("version") is not None else None,
            plugin_path=_installed_plugin_path(plugin) if plugin else None,
            marketplace_fingerprint=marketplace_fingerprint,
        )

    def marketplace_add(self, *, version: str | None = None) -> tuple[list[str], list[str]]:
        tag = f"v{version}" if version else TAG
        override = os.environ.get("KISEKI_DA_MARKETPLACE_SOURCE")
        if override:
            local = Path(override).expanduser().resolve()
            if not local.is_dir():
                raise InstallerError("KISEKI_DA_MARKETPLACE_SOURCEは既存local directoryだけを指定できます。")
            source = str(local)
        else:
            source = f"https://github.com/{MARKETPLACE_REPO}.git"
        if self.host == "claude-code":
            if not override:
                source += f"#{tag}"
            do = self.argv("plugin", "marketplace", "add", source, "--scope", "user")
            undo = self.argv("plugin", "marketplace", "remove", MARKETPLACE_ID, "--scope", "user")
        else:
            do = (self.argv("plugin", "marketplace", "add", source, "--json") if override
                  else self.argv("plugin", "marketplace", "add", source, "--ref", tag, "--json"))
            undo = self.argv("plugin", "marketplace", "remove", MARKETPLACE_ID, "--json")
        return do, undo

    def marketplace_remove(self, *, old_version: str | None = None) -> tuple[list[str], list[str]]:
        if self.host == "claude-code":
            do = self.argv("plugin", "marketplace", "remove", MARKETPLACE_ID, "--scope", "user")
        else:
            do = self.argv("plugin", "marketplace", "remove", MARKETPLACE_ID, "--json")
        undo, _ = self.marketplace_add(version=old_version)
        return do, undo

    def plugin_add(self) -> tuple[list[str], list[str]]:
        selector = f"{PLUGIN_ID}@{MARKETPLACE_ID}"
        if self.host == "claude-code":
            python_config = f"python_executable={Path(sys.executable).resolve()}"
            do = self.argv("plugin", "install", selector, "--scope", "user", "--config", python_config, "--yes")
            undo = self.argv("plugin", "uninstall", selector, "--scope", "user", "--keep-data", "--yes")
        else:
            do = self.argv("plugin", "add", selector, "--json")
            undo = self.argv("plugin", "remove", selector, "--json")
        return do, undo

    def plugin_remove(self) -> tuple[list[str], list[str]]:
        selector = f"{PLUGIN_ID}@{MARKETPLACE_ID}"
        if self.host == "claude-code":
            do = self.argv("plugin", "uninstall", selector, "--scope", "user", "--keep-data", "--yes")
            python_config = f"python_executable={Path(sys.executable).resolve()}"
            undo = self.argv("plugin", "install", selector, "--scope", "user", "--config", python_config, "--yes")
        else:
            do = self.argv("plugin", "remove", selector, "--json")
            undo = self.argv("plugin", "add", selector, "--json")
        return do, undo


def expand_hosts(value: str | list[str] | tuple[str, ...]) -> list[str]:
    if isinstance(value, str):
        values = [value]
    else:
        values = list(value)
    if not values:
        raise InstallerError("hostを1件以上指定してください。")
    if "all" in values:
        return ["claude-code", "codex"]
    unknown = [host for host in values if host not in MIN_VERSIONS]
    if unknown:
        raise InstallerError("未対応hostです: " + ", ".join(unknown))
    return list(dict.fromkeys(values))
