"""Archive only unchanged Kiseki skill copies, with a local recovery journal."""
from __future__ import annotations

import datetime as dt
import os
import shutil
import uuid
from pathlib import Path
from typing import Any

from .packs import MAIN_SKILLS, _tree_files, _tree_hash, skill_catalog
from .util import InstallerError, atomic_write_json


def _inside(path: Path, other: Path) -> bool:
    return path == other or path.is_relative_to(other)


def _discovered_path(path: Path) -> bool:
    parts = path.parts
    # Include both direct user/project skill roots and nested plugin skill roots.
    return any(part == "skills" and any(parent in {".agents", ".codex", ".claude"}
                                         for parent in parts[:index])
               for index, part in enumerate(parts))


def _paths(source: Path, visible: Path, archive: Path) -> tuple[Path, Path, Path]:
    archive = Path(archive)
    if not archive.is_absolute():
        raise InstallerError("archiveは明示的な絶対パスで指定してください。")
    visible = Path(visible).expanduser().absolute()
    if visible.is_symlink() or archive.is_symlink():
        raise InstallerError("visibleとarchiveにsymlinkは指定できません。")
    source = Path(source).expanduser().resolve()
    visible = visible.resolve()
    original_archive = archive
    archive = archive.resolve()
    if _inside(archive, source) or _inside(archive, visible) or _inside(visible, archive):
        raise InstallerError("archiveはsourceおよびvisibleと重ならない場所に指定してください。")
    if _discovered_path(original_archive) or _discovered_path(archive):
        raise InstallerError("archiveを通常のスキル発見ディレクトリ内には置けません。")
    for path in (visible, archive):
        if path.exists() and not path.is_dir():
            raise InstallerError(f"通常のディレクトリが必要です: {path}")
    return source, visible, archive


def _probe(path: Path) -> tuple[str | None, str | None]:
    if path.is_symlink() or not path.is_dir():
        return None, "not_regular_directory"
    try:
        return _tree_hash(path, _tree_files(path)), None
    except (InstallerError, OSError):
        return None, "symlink_special_or_unreadable"


def _rollback(rows: list[dict[str, Any]], visible: Path, holding: Path) -> list[str]:
    errors = []
    for row in reversed(rows):
        if row["state"] == "pending":
            continue
        original = visible / row["name"]
        held = holding / row["name"]
        copied = Path(row["archived_path"])
        if original.exists() or original.is_symlink():
            errors.append(f"新しいvisibleを上書きせず保持: {original}")
            continue
        try:
            if row["state"] == "archived" and _probe(held)[0] != row["sha256"]:
                # rmtree may have failed partway through an original tree.
                # Restore the complete backup; retain any remainder for review.
                if _probe(copied)[0] != row["sha256"]:
                    raise InstallerError(f"退避済みコピーが変更されています: {copied}")
                shutil.copytree(copied, original, symlinks=True)
            elif held.exists() or held.is_symlink():
                os.rename(held, original)
            elif row["state"] == "archived" and copied.is_dir():
                # A later cleanup failure can occur after an earlier original
                # has been removed. Restore that verified archived copy.
                if _probe(copied)[0] != row["sha256"]:
                    raise InstallerError(f"退避済みコピーが変更されています: {copied}")
                shutil.copytree(copied, original, symlinks=True)
            else:
                raise InstallerError(f"復元用の元ディレクトリがありません: {held}")
            row["state"] = "restored"
        except (OSError, InstallerError) as exc:
            errors.append(str(exc))
    try:
        holding.rmdir()
    except FileNotFoundError:
        pass
    except OSError as exc:
        errors.append(f"復元用ディレクトリを保持: {holding}: {exc}")
    return errors


def migrate_skills(source: Path, visible: Path, archive: Path, *, keep: list[str] | None = None,
                   dry_run: bool = True) -> dict[str, Any]:
    """Plan or archive exact, unselected original copies; preserve all others.

    The archive receives a transaction directory with ``journal.json`` and
    ``skills/<name>``. The temporary holding directory lives on the visible
    filesystem, so the source claim remains an atomic rename even when archive
    is on another volume. A failed run restores originals and retains its
    journal and any archived copies for inspection.
    """
    source, visible, archive = _paths(source, visible, archive)
    catalog = {row["name"]: row for row in skill_catalog(source)}
    if any(Path(row["source"]).parent == visible for row in catalog.values()):
        raise InstallerError("保管パックの原本自体は移行できません。visibleには発見対象のコピーを指定してください。")
    keep = list(MAIN_SKILLS) if keep is None else keep
    if (not isinstance(keep, (list, tuple)) or not all(isinstance(name, str) for name in keep)
            or len(set(keep)) != len(keep) or any(name not in catalog for name in keep)):
        raise InstallerError("keepはパック内の重複しないスキル名で指定してください。")
    preserved: list[dict[str, Any]] = []
    planned = []
    present = set()
    for path in sorted(visible.iterdir()) if visible.exists() else []:
        name = path.name
        present.add(name)
        expected = catalog.get(name)
        if expected is None:
            preserved.append({"name": name, "path": str(path), "reason": "not_in_pack"})
        elif name in keep:
            preserved.append({"name": name, "path": str(path), "reason": "selected"})
        else:
            actual, error = _probe(path)
            if actual == expected["sha256"]:
                planned.append({"name": name, "path": str(path), "sha256": actual})
            else:
                preserved.append({"name": name, "path": str(path), "reason": error or "modified",
                                  "actual_sha256": actual, "expected_sha256": expected["sha256"]})
    result: dict[str, Any] = {
        "dry_run": dry_run, "visible": str(visible), "archive": str(archive), "keep": list(keep),
        "planned": planned, "moved": [], "preserved": preserved,
        "already_absent": sorted(set(catalog) - present), "journal": None,
    }
    if dry_run or not planned:
        return result

    transaction_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid.uuid4().hex
    transaction = archive / transaction_id
    holding = visible / (".kiseki-migration-" + transaction_id)
    journal = transaction / "journal.json"
    rows = [{**row, "state": "pending", "archived_path": str(transaction / "skills" / row["name"]),
             "holding_path": str(holding / row["name"])} for row in planned]
    record: dict[str, Any] = {
        "schema": 1, "transaction": transaction_id, "status": "preparing", "visible": str(visible),
        "archive": str(archive), "holding": str(holding), "skills": rows,
    }
    archive.mkdir(parents=True, exist_ok=True)
    transaction.mkdir()
    (transaction / "skills").mkdir()
    atomic_write_json(journal, record, mode=0o600)
    try:
        holding.mkdir()
        for row in rows:
            original = visible / row["name"]
            held = holding / row["name"]
            copied = Path(row["archived_path"])
            if _probe(original)[0] != row["sha256"]:
                raise InstallerError(f"確認後にスキルが変更されました: {original}")
            row["state"] = "claiming"
            atomic_write_json(journal, record, mode=0o600)
            try:
                os.rename(original, held)
            except OSError:
                row["state"] = "pending"
                raise
            row["state"] = "held"
            atomic_write_json(journal, record, mode=0o600)
            if _probe(held)[0] != row["sha256"]:
                raise InstallerError(f"移動中にスキルが変更されました: {held}")
            shutil.copytree(held, copied, symlinks=True)
            if _probe(copied)[0] != row["sha256"] or _probe(held)[0] != row["sha256"]:
                raise InstallerError(f"退避コピーが原本と一致しません: {row['name']}")
            row["state"] = "copied"
            atomic_write_json(journal, record, mode=0o600)
        # Verify every claimed original once more before removing any of them.
        if any(_probe(holding / row["name"])[0] != row["sha256"] for row in rows):
            raise InstallerError("退避中に元スキルが変更されました。")
        record["status"] = "copied"
        atomic_write_json(journal, record, mode=0o600)
        for row in rows:
            # Record recovery from the archive before cleanup can partially fail.
            row["state"] = "archived"
            atomic_write_json(journal, record, mode=0o600)
            shutil.rmtree(holding / row["name"])
        holding.rmdir()
        record["status"] = "committed"
        atomic_write_json(journal, record, mode=0o600)
    except BaseException as exc:
        errors = _rollback(rows, visible, holding)
        record.update(status="rollback_incomplete" if errors else "rolled_back", error=str(exc),
                      rollback_errors=errors)
        try:
            atomic_write_json(journal, record, mode=0o600)
        except OSError as write_error:
            errors.append(f"journal保存失敗: {write_error}")
        status = "復元が未完了" if errors else "復元済み"
        raise InstallerError(f"スキル移行に失敗しました（{status}）: {exc}; journal: {journal}") from None
    result["moved"] = [{"name": row["name"], "path": row["path"], "sha256": row["sha256"],
                        "archived_path": row["archived_path"]} for row in rows]
    result["journal"] = str(journal)
    return result
