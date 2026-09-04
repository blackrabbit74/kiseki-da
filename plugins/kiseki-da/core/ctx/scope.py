"""Project activation and state isolation for Kiseki DA.

The activation registry is deliberately small and contains no user content.  A
project entry maps a canonical working-tree path to an opaque UUID; all mutable
project state lives below ``<KISEKI_DA_HOME>/projects/<uuid>``.

Reading the registry never creates files.  This is important for hooks: when
project mode is enabled, an unregistered cwd must be a true no-op.
"""
from __future__ import annotations

import json
import os
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path

from core.ctx import store as _store
from core.ctx.store import UserError

REGISTRY_SCHEMA = 1
REGISTRY_NAME = "projects.json"
MODES = ("user", "project")


@dataclass(frozen=True)
class ScopeResolution:
    active: bool
    mode: str
    common_home: Path
    state_home: Path | None
    project_id: str | None = None
    project_path: Path | None = None

    def as_dict(self) -> dict:
        data = asdict(self)
        for key in ("common_home", "state_home", "project_path"):
            if data[key] is not None:
                data[key] = str(data[key])
        return data


def canonical_path(path: str | os.PathLike[str]) -> Path:
    """Return the comparison form used by the registry (without requiring existence)."""
    return Path(path).expanduser().resolve(strict=False)


def registry_path(home: Path | None = None) -> Path:
    return canonical_path(home if home is not None else _store.kiseki_da_home()) / REGISTRY_NAME


def empty_registry(mode: str = "user") -> dict:
    if mode not in MODES:
        raise UserError(f"scope は {'/'.join(MODES)} のいずれかです: {mode}")
    return {"schema": REGISTRY_SCHEMA, "mode": mode, "projects": []}


def _validate_registry(data: object) -> dict:
    if not isinstance(data, dict):
        raise UserError("projects.json は JSON オブジェクトではありません")
    mode = data.get("mode", "user")
    if mode not in MODES:
        raise UserError(f"projects.json の mode が不正です: {mode}")
    rows = data.get("projects", [])
    if not isinstance(rows, list):
        raise UserError("projects.json の projects は配列で指定してください")
    clean: list[dict] = []
    ids: set[str] = set()
    paths: set[str] = set()
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            raise UserError(f"projects[{i}] はオブジェクトではありません")
        pid, raw_path = row.get("id"), row.get("path")
        if not isinstance(pid, str) or not pid:
            raise UserError(f"projects[{i}].id がありません")
        try:
            canonical_id = str(uuid.UUID(pid))
        except (ValueError, AttributeError):
            raise UserError(f"projects[{i}].id は UUID で指定してください") from None
        if pid.lower() != canonical_id:
            raise UserError(f"projects[{i}].id は正規化した UUID で指定してください")
        if not isinstance(raw_path, str) or not raw_path:
            raise UserError(f"projects[{i}].path がありません")
        path = str(canonical_path(raw_path))
        path_key = os.path.normcase(path)
        if canonical_id in ids or path_key in paths:
            raise UserError("projects.json に重複した id または path があります")
        ids.add(canonical_id)
        paths.add(path_key)
        item = dict(row)
        item["id"], item["path"] = canonical_id, path
        clean.append(item)
    return {**data, "schema": int(data.get("schema", REGISTRY_SCHEMA)), "mode": mode, "projects": clean}


def load_registry(home: Path | None = None) -> dict:
    """Read the activation registry without creating state."""
    path = registry_path(home)
    if not path.is_file():
        return empty_registry()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise UserError(f"projects.json を読めません: {exc}") from None
    return _validate_registry(data)


def save_registry(home: Path, registry: dict) -> Path:
    """Validate and atomically save a registry.  Intended for installer/CLI transactions."""
    data = _validate_registry(registry)
    path = registry_path(home)
    _store._atomic_write(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    return path


def set_mode(home: Path, mode: str) -> dict:
    data = load_registry(home)
    data["mode"] = mode
    save_registry(home, data)
    return data


def _project_profile_text() -> str:
    # Identity and constraints live only in the common profile.  The empty
    # compatibility tables keep the TOML consumable by schema-1 readers.
    return (
        "schema = 2\n\n"
        "[identity]\n\n"
        "[da]\n"
        'name = ""\n\n'
        "[persona]\n"
    )


def add_project(home: Path, path: str | os.PathLike[str]) -> dict:
    """Register a project and create its isolated state directory."""
    root = canonical_path(home)
    project_path = canonical_path(path)
    if not project_path.is_dir():
        raise UserError(f"プロジェクトのディレクトリがありません: {project_path}")
    data = load_registry(root)
    path_key = os.path.normcase(str(project_path))
    for row in data["projects"]:
        if os.path.normcase(row["path"]) == path_key:
            return row
    row = {"id": str(uuid.uuid4()), "path": str(project_path), "created": _store.now_iso()}
    project_home = root / "projects" / row["id"]
    project_home.mkdir(parents=True, exist_ok=False)
    try:
        os.chmod(project_home, 0o700)
    except OSError:  # Windows ACLs are managed by the parent user profile.
        pass
    for sub in ("tasks", "archive", "snapshots", "session"):
        (project_home / sub).mkdir(parents=True, exist_ok=True)
    _store._atomic_write(project_home / "profile.toml", _project_profile_text())
    data["projects"].append(row)
    data["mode"] = "project"
    try:
        save_registry(root, data)
    except BaseException:
        # Do not erase a directory that predated this call: exist_ok=False
        # above guarantees this directory belongs to this transaction.
        import shutil
        shutil.rmtree(project_home)
        raise
    return row


def list_projects(home: Path | None = None) -> list[dict]:
    return [dict(row) for row in load_registry(home)["projects"]]


def _select_project(data: dict, selector: str | os.PathLike[str]) -> dict | None:
    raw = str(selector)
    by_path = os.path.normcase(str(canonical_path(raw)))
    for row in data["projects"]:
        if row["id"] == raw or os.path.normcase(row["path"]) == by_path:
            return row
    return None


def remove_project(home: Path, selector: str | os.PathLike[str]) -> dict:
    """Deactivate a project while preserving its project state for recovery."""
    data = load_registry(home)
    row = _select_project(data, selector)
    if row is None:
        raise UserError(f"登録済みプロジェクトがありません: {selector}")
    data["projects"] = [x for x in data["projects"] if x["id"] != row["id"]]
    save_registry(home, data)
    return {**row, "state_preserved": str(canonical_path(home) / "projects" / row["id"])}


def _contains(root: Path, child: Path) -> bool:
    try:
        child.relative_to(root)
        return True
    except ValueError:
        return False


def resolve_scope(home: Path | None, cwd: str | os.PathLike[str] | None) -> ScopeResolution:
    """Resolve cwd to user/project state.  No filesystem writes are performed."""
    common = canonical_path(home if home is not None else _store.kiseki_da_home())
    data = load_registry(common)
    if data["mode"] == "user":
        return ScopeResolution(True, "user", common, common)
    if not cwd:
        return ScopeResolution(False, "project", common, None)
    current = canonical_path(cwd)
    matches = [row for row in data["projects"] if _contains(canonical_path(row["path"]), current)]
    if not matches:
        return ScopeResolution(False, "project", common, None)
    row = max(matches, key=lambda x: len(canonical_path(x["path"]).parts))
    return ScopeResolution(True, "project", common, common / "projects" / row["id"],
                           row["id"], canonical_path(row["path"]))


def is_active(home: Path | None, cwd: str | os.PathLike[str] | None) -> bool:
    return resolve_scope(home, cwd).active


def scoped_store(home: Path | None, cwd: str | os.PathLike[str] | None, sid: str | None = None):
    """Return a Store for cwd, or None when project mode is inactive."""
    from core.ctx.store import Store
    resolved = resolve_scope(home, cwd)
    if not resolved.active or resolved.state_home is None:
        return None
    if resolved.mode == "user":
        return Store(home=resolved.state_home, sid=sid)
    return Store(home=resolved.state_home, sid=sid, common_home=resolved.common_home,
                 project_id=resolved.project_id)
