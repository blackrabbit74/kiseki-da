"""Crash-visible transactions with filesystem snapshots and external undo steps."""
from __future__ import annotations

import datetime as dt
import hashlib
import os
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Callable, Sequence

try:  # pragma: no cover - platform branch
    import fcntl as _fcntl
except ImportError:  # pragma: no cover
    _fcntl = None
try:  # pragma: no cover - platform branch
    import msvcrt as _msvcrt
except ImportError:  # pragma: no cover
    _msvcrt = None

from .util import InstallerError, atomic_write_json, atomic_write_text, read_json, redact_sensitive, remove_path


Runner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]


class _MutationLock:
    """Process-held, crash-safe lock serialising state-changing operations."""

    def __init__(self, path: Path):
        self.path = path
        self.stream = None

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        stream = self.path.open("a+b")
        try:
            if _fcntl is not None:
                _fcntl.flock(stream.fileno(), _fcntl.LOCK_EX | _fcntl.LOCK_NB)
            elif _msvcrt is not None:
                stream.seek(0, os.SEEK_END)
                if stream.tell() == 0:
                    stream.write(b"\0")
                    stream.flush()
                stream.seek(0)
                _msvcrt.locking(stream.fileno(), _msvcrt.LK_NBLCK, 1)
            else:  # Supported targets always provide one implementation.
                raise OSError("filesystem locking is unavailable")
        except OSError:
            stream.close()
            raise InstallerError("別のKiseki DA変更transactionが実行中です。") from None
        self.stream = stream

    def release(self) -> None:
        stream, self.stream = self.stream, None
        if stream is None:
            return
        try:
            if _fcntl is not None:
                _fcntl.flock(stream.fileno(), _fcntl.LOCK_UN)
            elif _msvcrt is not None:
                stream.seek(0)
                _msvcrt.locking(stream.fileno(), _msvcrt.LK_UNLCK, 1)
        finally:
            stream.close()


def _transactions(home: Path) -> Path:
    return home / "transactions"


def _load_journals(home: Path) -> list[tuple[Path, dict]]:
    root = _transactions(home)
    if not root.is_dir():
        return []
    found: list[tuple[Path, dict]] = []
    for path in sorted(root.glob("*/journal.json")):
        value = read_json(path, {})
        if isinstance(value, dict):
            found.append((path, value))
    return found


def active_transactions(home: Path) -> list[str]:
    return [str(data.get("id", path.parent.name)) for path, data in _load_journals(home)
            if data.get("status") in {"active", "rolling_back", "rollback_incomplete"}]


def ensure_no_active(home: Path) -> None:
    active = active_transactions(home)
    if active:
        raise InstallerError(
            "未完了transactionがあります。先に rollback を実行してください: " + ", ".join(active)
        )


class Transaction:
    """A transaction whose journal is sufficient for explicit or automatic rollback."""

    def __init__(self, home: Path, action: str, *, preserve_user_state_on_manual: bool = True):
        self.home = home.resolve()
        self._mutation_lock = _MutationLock(_transactions(self.home) / ".mutation.lock")
        self._mutation_lock.acquire()
        try:
            ensure_no_active(self.home)
        except BaseException:
            self._mutation_lock.release()
            raise
        stamp = dt.datetime.now().strftime("%Y%m%dT%H%M%S%f")
        self.id = f"{stamp}-{uuid.uuid4().hex[:8]}"
        self.root = _transactions(self.home) / self.id
        self.backups = self.root / "backups"
        self.journal_path = self.root / "journal.json"
        self.data: dict = {
            "schema": 1,
            "id": self.id,
            "action": action,
            "home": str(self.home),
            "status": "active",
            "started_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
            "filesystem": [],
            "external": [],
            "error": None,
            "preserve_user_state_on_manual": bool(preserve_user_state_on_manual),
        }
        try:
            self.backups.mkdir(parents=True, exist_ok=False)
            try:
                os.chmod(self.home, 0o700)
            except OSError:
                pass
            self._save()
        except BaseException:
            self._mutation_lock.release()
            raise

    def _save(self) -> None:
        atomic_write_json(self.journal_path, self.data, mode=0o600)

    def _inside_home(self, path: Path) -> Path:
        path = path.resolve(strict=False)
        try:
            path.relative_to(self.home)
        except ValueError:
            raise InstallerError(f"transaction対象がKISEKI_DA_HOME外です: {path}") from None
        return path

    def _backup(self, target: Path, *, external: bool = False, external_mutable: bool = False) -> None:
        target = target.absolute() if external else self._inside_home(target)
        for entry in self.data["filesystem"]:
            if entry["target"] == str(target):
                if external_mutable and not entry.get("external_mutable"):
                    entry["external_mutable"] = True
                    entry["applied"] = self._signature(target)
                    self._save()
                return
        index = len(self.data["filesystem"])
        backup = self.backups / f"{index:04d}"
        if target.is_symlink():
            kind = "symlink"
            value = os.readlink(target)
        elif target.is_file():
            kind = "file"
            shutil.copy2(target, backup)
            value = None
        elif target.is_dir():
            kind = "directory"
            shutil.copytree(target, backup, symlinks=True)
            value = None
        else:
            kind = "absent"
            value = None
        self.data["filesystem"].append({
            "target": str(target),
            "external": external,
            "kind": kind,
            "backup": str(backup) if kind in {"file", "directory"} else None,
            "value": value,
            "external_mutable": bool(external_mutable),
        })
        self._save()

    @staticmethod
    def _signature(target: Path) -> dict:
        if target.is_symlink():
            return {"kind": "symlink", "sha256": hashlib.sha256(os.readlink(target).encode()).hexdigest()}
        if target.is_file():
            return {"kind": "file", "sha256": hashlib.sha256(target.read_bytes()).hexdigest()}
        if target.is_dir():
            rows: list[str] = []
            for path in sorted(target.rglob("*")):
                rel = path.relative_to(target).as_posix()
                if path.is_symlink():
                    rows.append(f"L {rel} {os.readlink(path)}")
                elif path.is_file():
                    rows.append(f"F {rel} {hashlib.sha256(path.read_bytes()).hexdigest()}")
                elif path.is_dir():
                    rows.append(f"D {rel}")
            return {"kind": "directory", "sha256": hashlib.sha256("\n".join(rows).encode()).hexdigest()}
        return {"kind": "absent", "sha256": None}

    def _mark_applied(self, target: Path) -> None:
        absolute = target.absolute()
        candidates = {str(absolute), str(target.resolve(strict=False))}
        for entry in self.data["filesystem"]:
            if entry["target"] in candidates:
                entry["applied"] = self._signature(Path(entry["target"]))
                self._save()
                return
        raise InstallerError(f"transaction backupがありません: {target}")

    def backup(self, target: Path) -> None:
        self._backup(target)

    def backup_external(self, target: Path) -> None:
        self._backup(target, external=True)

    def track_external_mutable(self, target: Path) -> None:
        """Back up a host config file that native manager commands will edit."""
        target = target.resolve(strict=False)
        self._backup(target, external=True, external_mutable=True)
        self._mark_applied(target)

    def track_created(self, target: Path) -> None:
        """Register a path created by a nested atomic writer for rollback."""
        target = self._inside_home(target)
        if any(entry["target"] == str(target) for entry in self.data["filesystem"]):
            return
        self.data["filesystem"].append({
            "target": str(target),
            "external": False,
            "kind": "absent",
            "backup": None,
            "value": None,
            "external_mutable": False,
            "applied": self._signature(target),
        })
        self._save()

    def capture_applied(self) -> None:
        """Record signatures for paths mutated by code outside Transaction helpers."""
        changed = False
        for entry in self.data["filesystem"]:
            if "applied" not in entry:
                entry["applied"] = self._signature(Path(entry["target"]))
                changed = True
        if changed:
            self._save()

    def _check_external_mutable(self) -> None:
        for entry in self.data["filesystem"]:
            if not entry.get("external_mutable") or not isinstance(entry.get("applied"), dict):
                continue
            target = Path(entry["target"])
            if self._signature(target) != entry["applied"]:
                raise InstallerError(f"host設定の同時変更を検出しました: {target}")

    def _refresh_external_mutable(self) -> None:
        changed = False
        for entry in self.data["filesystem"]:
            if entry.get("external_mutable"):
                entry["applied"] = self._signature(Path(entry["target"]))
                changed = True
        if changed:
            self._save()

    def write_text(self, target: Path, text: str, *, mode: int | None = None) -> None:
        self.backup(target)
        atomic_write_text(target, text, mode=mode)
        self._mark_applied(target)

    def write_json(self, target: Path, value: object, *, mode: int | None = None) -> None:
        self.backup(target)
        atomic_write_json(target, value, mode=mode)
        self._mark_applied(target)

    def write_external_text(self, target: Path, text: str, *, mode: int | None = None) -> None:
        target = target.resolve(strict=False)
        self.backup_external(target)
        atomic_write_text(target, text, mode=mode)
        self._mark_applied(target)

    def replace_tree(self, source: Path, target: Path) -> None:
        self.backup(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        stage = target.parent / f".{target.name}.stage-{self.id}"
        remove_path(stage)
        shutil.copytree(source, stage, symlinks=True)
        remove_path(target)
        os.replace(stage, target)
        self._mark_applied(target)

    def remove(self, target: Path) -> None:
        self.backup(target)
        remove_path(target)
        self._mark_applied(target)

    def remove_external(self, target: Path) -> None:
        self.backup_external(target)
        remove_path(target)
        self._mark_applied(target)

    def external(self, argv: Sequence[str], undo: Sequence[str] | None, runner: Runner) -> subprocess.CompletedProcess[str]:
        raw_commands = [*map(str, argv), *(map(str, undo) if undo else [])]
        command_text = " ".join(raw_commands)
        if redact_sensitive(command_text) != command_text:
            raise InstallerError("host manager commandへ秘密情報を埋め込むことはできません。")
        self._check_external_mutable()
        entry = {
            "argv": list(map(str, argv)),
            "undo": list(map(str, undo)) if undo else None,
            "state": "pending",
            "returncode": None,
        }
        self.data["external"].append(entry)
        self._save()
        result = runner(argv)
        entry["returncode"] = result.returncode
        entry["stdout"] = redact_sensitive(result.stdout or "")[-4000:]
        entry["stderr"] = redact_sensitive(result.stderr or "")[-4000:]
        entry["state"] = "applied" if result.returncode == 0 else "failed"
        self._save()
        # Native managers can update config files that the caller pre-backed
        # up. Bind those exact post-command signatures even on partial failure.
        self._refresh_external_mutable()
        if result.returncode != 0:
            detail = redact_sensitive(result.stderr or result.stdout or "終了コード " + str(result.returncode)).strip()
            raise InstallerError(f"host managerが失敗しました: {detail}")
        return result

    def on_rollback(self, argv: Sequence[str]) -> None:
        """Register a compensating command before a later change makes it necessary."""
        values = list(map(str, argv))
        if redact_sensitive(" ".join(values)) != " ".join(values):
            raise InstallerError("rollback commandへ秘密情報を埋め込むことはできません。")
        self.data["external"].append({"argv": [], "undo": values, "state": "undo_only", "returncode": None})
        self._save()

    def retain_external_tree(self, source: Path, target: Path) -> None:
        """Publish an immutable cache; keep it even if a new session starts before rollback."""
        target = target.absolute()
        expected = self._signature(source)
        if target.exists() or target.is_symlink():
            if self._signature(target) != expected:
                raise InstallerError(f"既存version cacheの内容が一致しません。上書きしません: {target}")
            return
        self.data.setdefault("retained_caches", []).append({"target": str(target), "signature": expected})
        self._save()
        target.parent.mkdir(parents=True, exist_ok=True)
        staged = target.parent / f".{target.name}.stage-{self.id}"
        try:
            shutil.copytree(source, staged, symlinks=True)
            if target.exists() or target.is_symlink():
                raise InstallerError(f"cache配置中に別の更新を検出しました: {target}")
            os.rename(staged, target)
        finally:
            remove_path(staged)

    def commit(self, **details: object) -> None:
        try:
            self.data["status"] = "committed"
            self.data["completed_at"] = dt.datetime.now().astimezone().isoformat(timespec="seconds")
            self.data["result"] = details
            self._save()
        finally:
            self._mutation_lock.release()

    def rollback(self, runner: Runner, *, error: BaseException | str | None = None) -> bool:
        try:
            self.data["status"] = "rolling_back"
            self.data["error"] = redact_sensitive(error) if error else None
            self._save()
            errors = _restore(self.data, runner, persist=self._save)
            self.data["rollback_errors"] = errors
            self.data["status"] = "rolled_back" if not errors else "rollback_incomplete"
            self.data["completed_at"] = dt.datetime.now().astimezone().isoformat(timespec="seconds")
            self._save()
            return not errors
        finally:
            self._mutation_lock.release()


def _manual_state_path(home: Path, target: Path) -> bool:
    """User data survives a manual rollback of an already committed operation."""
    try:
        rel = target.resolve(strict=False).relative_to(home.resolve())
    except ValueError:
        return False
    if not rel.parts:
        return False
    return rel.parts[0] in {
        "profile.toml", "events.jsonl", "candidates.jsonl", "tasks", "archive", "snapshots",
        "session", "projects", "projects.json",
    }


def _restore(
    data: dict, runner: Runner, *, manual_committed: bool = False,
    persist: Callable[[], None] | None = None,
) -> list[str]:
    errors: list[str] = []
    external_conflict = False
    for entry in reversed(data.get("external", [])):
        if entry.get("undo_state") == "applied":
            continue
        if entry.get("undo_state") == "running":
            errors.append("external: 前回中断時のnative undo完了状態を確認できないため再実行しません")
            continue
        undo = entry.get("undo")
        if not undo or entry.get("state") not in {"pending", "applied", "failed", "undo_only"}:
            continue
        try:
            for file_entry in data.get("filesystem", []):
                if not file_entry.get("external_mutable") or not isinstance(file_entry.get("applied"), dict):
                    continue
                target = Path(file_entry["target"])
                if Transaction._signature(target) != file_entry["applied"]:
                    errors.append(f"filesystem {target}: host設定の同時変更を検出したためnative undoを停止しました")
                    external_conflict = True
                    break
            if external_conflict:
                continue
            entry["undo_state"] = "running"
            if persist:
                persist()
            result = runner(undo)
            if result.returncode != 0:
                detail = redact_sensitive(result.stderr or result.stdout or str(result.returncode)).strip()
                errors.append(f"external: {detail}")
                entry["undo_state"] = "failed"
            else:
                entry["undo_state"] = "applied"
                for file_entry in data.get("filesystem", []):
                    if file_entry.get("external_mutable"):
                        file_entry["applied"] = Transaction._signature(Path(file_entry["target"]))
            if persist:
                persist()
        except Exception as exc:  # noqa: BLE001 - rollback must continue
            errors.append(f"external: {type(exc).__name__}: {redact_sensitive(exc)}")
    for entry in reversed(data.get("filesystem", [])):
        if entry.get("restored") is True:
            continue
        target = Path(entry["target"])
        if (manual_committed and data.get("preserve_user_state_on_manual", True)
                and not entry.get("external") and _manual_state_path(Path(data["home"]), target)):
            continue
        applied = entry.get("applied")
        if entry.get("restore_state") == "running":
            kind = entry.get("kind")
            if kind == "absent":
                original = {"kind": "absent", "sha256": None}
            elif kind in {"file", "directory"}:
                original = Transaction._signature(Path(entry["backup"]))
            elif kind == "symlink":
                original = {"kind": "symlink", "sha256": hashlib.sha256(str(entry["value"]).encode()).hexdigest()}
            else:
                original = None
            if isinstance(original, dict) and Transaction._signature(target) == original:
                entry["restored"] = True
                entry["restore_state"] = "restored"
                if persist:
                    persist()
                continue
        if isinstance(applied, dict):
            try:
                current = Transaction._signature(target)
            except OSError as exc:
                errors.append(f"filesystem {target}: current hash failed: {exc}")
                continue
            if current != applied:
                errors.append(f"filesystem {target}: installer適用後の変更を検出したため復元しません")
                continue
        try:
            entry["restore_state"] = "running"
            if persist:
                persist()
            remove_path(target)
            kind = entry.get("kind")
            if kind == "file":
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(Path(entry["backup"]), target)
            elif kind == "directory":
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(Path(entry["backup"]), target, symlinks=True)
            elif kind == "symlink":
                target.parent.mkdir(parents=True, exist_ok=True)
                target.symlink_to(entry["value"])
            entry["restored"] = True
            entry["restore_state"] = "restored"
            if persist:
                persist()
        except Exception as exc:  # noqa: BLE001 - report every failed restoration
            errors.append(f"filesystem {target}: {type(exc).__name__}: {exc}")
    home = Path(data.get("home", "/__kiseki_da_invalid_home__"))
    parents = sorted({Path(entry["target"]).parent for entry in data.get("filesystem", [])
                      if not entry.get("external")},
                     key=lambda path: len(path.parts), reverse=True)
    for parent in parents:
        while parent != home:
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent
    return errors


def rollback_saved(home: Path, transaction_id: str, runner: Runner) -> tuple[str, bool, list[str]]:
    home = home.resolve()
    lock = _MutationLock(_transactions(home) / ".mutation.lock")
    lock.acquire()
    try:
        journals = _load_journals(home)
        rollbackable = {"committed", "active", "rolling_back", "rollback_incomplete"}
        candidates = [item for item in journals if item[1].get("status") in rollbackable]
        if transaction_id == "latest":
            if not candidates:
                raise InstallerError("rollbackできるtransactionがありません。")
            path, data = candidates[-1]
        else:
            matches = [item for item in journals if item[1].get("id", item[0].parent.name) == transaction_id]
            if not matches:
                raise InstallerError(f"transactionがありません: {transaction_id}")
            path, data = matches[0]
            if data.get("status") not in rollbackable:
                raise InstallerError(f"transactionはrollback対象ではありません: {transaction_id} ({data.get('status')})")
            if candidates and path != candidates[-1][0]:
                raise InstallerError("安全のため最新transactionだけをrollbackできます。")
        was_committed = data.get("status") == "committed" or data.get("manual_from_committed") is True
        data["manual_from_committed"] = was_committed
        data["status"] = "rolling_back"
        atomic_write_json(path, data, mode=0o600)
        errors = _restore(
            data, runner, manual_committed=was_committed,
            persist=lambda: atomic_write_json(path, data, mode=0o600),
        )
        data["rollback_errors"] = errors
        data["status"] = "rolled_back_manual" if not errors else "rollback_incomplete"
        data["completed_at"] = dt.datetime.now().astimezone().isoformat(timespec="seconds")
        atomic_write_json(path, data, mode=0o600)
        return str(data.get("id", path.parent.name)), not errors, errors
    finally:
        lock.release()
