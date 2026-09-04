"""Acquire an explicitly requested update and verify its release checksum."""
from __future__ import annotations

import contextlib
import json
import os
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Iterator

from .constants import MARKETPLACE_REPO, VERSION
from .util import InstallerError, verify_checksum


def _download(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "kiseki-da-installer"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response, destination.open("wb") as stream:
            shutil.copyfileobj(response, stream)
    except Exception as exc:  # noqa: BLE001 - convert transport failures to a stable user error
        raise InstallerError(f"updateのダウンロードに失敗しました: {exc}") from None


def _safe_extract(archive: Path, destination: Path) -> None:
    base = destination.resolve()
    try:
        with zipfile.ZipFile(archive) as bundle:
            for item in bundle.infolist():
                resolved = (destination / item.filename).resolve()
                try:
                    resolved.relative_to(base)
                except ValueError:
                    raise InstallerError(f"ZIP内に不正なパスがあります: {item.filename}") from None
                mode = item.external_attr >> 16
                if (mode & 0o170000) == 0o120000:
                    raise InstallerError(f"ZIP内のsymlinkは許可されません: {item.filename}")
            bundle.extractall(destination)
    except zipfile.BadZipFile:
        raise InstallerError(f"release ZIPを読めません: {archive}") from None


def _source_root(extracted: Path) -> Path:
    if (extracted / "VERSION").is_file() and (extracted / "install.py").is_file():
        return extracted
    matches = [path for path in extracted.iterdir()
               if path.is_dir() and (path / "VERSION").is_file() and (path / "install.py").is_file()]
    if len(matches) != 1:
        raise InstallerError("release ZIP内のKiseki DA rootを一意に特定できません。")
    return matches[0]


def _select_release(payload: object, *, allow_prerelease: bool) -> dict:
    rows = payload if isinstance(payload, list) else [payload]
    for row in rows:
        if not isinstance(row, dict) or row.get("draft"):
            continue
        if row.get("prerelease") and not allow_prerelease:
            continue
        assets = row.get("assets")
        if not isinstance(assets, list):
            continue
        if any(str(item.get("name", "")).startswith("kiseki-da-") and
               str(item.get("name", "")).endswith(".zip") for item in assets if isinstance(item, dict)):
            return row
    raise InstallerError("更新可能なKiseki DA releaseがありません。")


@contextlib.contextmanager
def update_source(explicit: str | None = None) -> Iterator[Path]:
    configured = explicit or os.environ.get("KISEKI_DA_UPDATE_SOURCE")
    if configured:
        path = Path(configured).expanduser().resolve()
        if not path.is_dir():
            raise InstallerError(f"update sourceがありません: {path}")
        yield path
        return

    # GitHub's /releases/latest excludes prereleases. Beta installations inspect
    # the release list explicitly; stable installations never select a prerelease.
    api = f"https://api.github.com/repos/{MARKETPLACE_REPO}/releases?per_page=20"
    request = urllib.request.Request(api, headers={"Accept": "application/vnd.github+json", "User-Agent": "kiseki-da-installer"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            release = _select_release(json.load(response), allow_prerelease="-" in VERSION)
    except Exception as exc:  # noqa: BLE001
        raise InstallerError(f"GitHub release情報を取得できません: {exc}") from None
    assets = release.get("assets", []) if isinstance(release, dict) else []
    zip_asset = next((item for item in assets
                      if str(item.get("name", "")).startswith("kiseki-da-")
                      and str(item.get("name", "")).endswith(".zip")), None)
    sums_asset = next((item for item in assets if item.get("name") == "SHA256SUMS"), None)
    if not zip_asset or not sums_asset:
        raise InstallerError("最新releaseにZIPまたはSHA256SUMSがありません。")
    with tempfile.TemporaryDirectory(prefix="kiseki-da-update-") as raw:
        temp = Path(raw)
        archive = temp / Path(zip_asset["name"]).name
        sums = temp / "SHA256SUMS"
        _download(str(zip_asset["browser_download_url"]), archive)
        _download(str(sums_asset["browser_download_url"]), sums)
        verify_checksum(archive, sums)
        extracted = temp / "source"
        extracted.mkdir()
        _safe_extract(archive, extracted)
        yield _source_root(extracted)
