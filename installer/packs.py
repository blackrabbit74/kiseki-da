"""Select and copy dormant skills and bounded, editable persona presets.

The catalog is read only on request. It does not register skills with a host or
claim that the external tools mentioned by a skill are available.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

from .util import InstallerError


MAIN_SKILLS = (
    "exploring-ideas", "clarifying-outcomes", "analyzing-assumptions", "comparing-options",
    "researching-with-sources", "reviewing-literature", "auditing-source-credibility",
    "retrieving-context", "extracting-insights", "synthesizing-documents",
    "defining-product-briefs", "defining-domain-terms", "designing-experiments",
    "testing-concepts", "mapping-strategy", "revising-plans", "reviewing-plan-consistency",
    "structuring-arguments",
)
_NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")


def _name(value: object) -> str:
    if not isinstance(value, str) or not _NAME.fullmatch(value):
        raise InstallerError(f"スキル／プリセット名が不正です: {value!r}")
    return value


def _skill_root(source: Path) -> Path:
    source = Path(source).expanduser().resolve()
    for candidate in (source / "skills", source / "packs" / "skills"):
        if candidate.is_symlink():
            raise InstallerError(f"スキルパックにsymlinkは使用できません: {candidate}")
        if candidate.is_dir() and any(candidate.glob("*/SKILL.md")):
            return candidate
    raise InstallerError(f"スキルパックがありません: {source}")


def _tree_files(root: Path) -> list[Path]:
    if root.is_symlink() or not root.is_dir():
        raise InstallerError(f"通常のディレクトリが必要です: {root}")
    files = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise InstallerError(f"パック内にsymlinkは使用できません: {path}")
        if path.is_file():
            files.append(path)
        elif not path.is_dir():
            raise InstallerError(f"パック内に通常ファイル以外があります: {path}")
    return files


def _tree_hash(root: Path, files: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_dir()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(b"D" + len(relative).to_bytes(8, "big") + relative)
    for path in files:
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(b"F" + len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def _frontmatter_value(frontmatter: str, key: str) -> str:
    match = re.search(rf"^{key}:\s*(.+)$", frontmatter, re.MULTILINE)
    if match is None:
        raise InstallerError(f"SKILL.mdに{key}がありません")
    value = match.group(1).strip()
    if value.startswith('"'):
        try:
            value = json.loads(value)
        except ValueError:
            raise InstallerError(f"SKILL.mdの{key}を読めません") from None
    elif value.startswith("'") and value.endswith("'"):
        value = value[1:-1].replace("''", "'")
    if not isinstance(value, str) or not value or value in {"|", ">", "|-", ">-"}:
        raise InstallerError(f"SKILL.mdの{key}は空でない1行の文字列が必要です")
    return value


def _skill_metadata(root: Path, name: str) -> dict[str, Any]:
    path = root / _name(name)
    if not path.is_dir():
        raise InstallerError(f"スキルがありません: {name}")
    files = _tree_files(path)
    skill = path / "SKILL.md"
    try:
        text = skill.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise InstallerError(f"SKILL.mdを読めません: {skill}: {exc}") from None
    match = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|\Z)", text, re.DOTALL)
    if match is None:
        raise InstallerError(f"SKILL.mdのfrontmatterがありません: {skill}")
    if _frontmatter_value(match.group(1), "name") != name:
        raise InstallerError(f"SKILL.mdのnameとディレクトリ名が一致しません: {name}")
    names = [item.relative_to(path).as_posix() for item in files]
    return {
        "name": name,
        "description": _frontmatter_value(match.group(1), "description"),
        "source": str(path),
        "sha256": _tree_hash(path, files),
        "files": names,
        "references": [name for name in names if name.startswith("references/")],
        "execution_status": "not_checked",
    }


def skill_catalog(source: Path) -> list[dict[str, Any]]:
    """Return a stable catalog without modifying host discovery configuration."""
    root = _skill_root(source)
    return [_skill_metadata(root, path.name) for path in sorted(root.iterdir())
            if path.is_dir() or path.is_symlink()]


def select_skills(source: Path, names: list[str]) -> list[dict[str, Any]]:
    """Validate the distinct 10–20 skills selected for a working environment."""
    if not isinstance(names, (list, tuple)) or not 10 <= len(names) <= 20:
        raise InstallerError("常用スキルは10〜20個指定してください。")
    normalized = [_name(name) for name in names]
    if len(set(normalized)) != len(normalized):
        raise InstallerError("常用スキルの指定が重複しています。")
    root = _skill_root(source)
    return [_skill_metadata(root, name) for name in normalized]


def _check_destination(destination: Path, names: list[str]) -> Path:
    destination = Path(destination).expanduser().absolute()
    if destination.is_symlink() or (destination.exists() and not destination.is_dir()):
        raise InstallerError(f"コピー先は通常のディレクトリが必要です: {destination}")
    for name in names:
        target = destination / name
        if target.exists() or target.is_symlink():
            raise InstallerError(f"既存ファイルを上書きしません: {target}")
    return destination


def _publish(staged: Path, destination: Path, names: list[str]) -> None:
    """Reserve each new tree exclusively and clean only this operation's trees."""
    destination = _check_destination(destination, names)
    destination.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    try:
        for name in names:
            target = destination / name
            target.mkdir()  # exclusive reservation; an existing empty tree is not ours
            created.append(target)
            for item in (staged / name).iterdir():
                os.rename(item, target / item.name)
    except BaseException:
        for target in reversed(created):
            shutil.rmtree(target)
        raise


def _copy_skills(rows: list[dict[str, Any]], destination: Path) -> list[dict[str, Any]]:
    names = [row["name"] for row in rows]
    destination = _check_destination(destination, names)
    for row in rows:
        origin = Path(row["source"]).resolve()
        if destination.resolve().is_relative_to(origin):
            raise InstallerError(f"スキル自身の中へコピーできません: {origin}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".kiseki-skills-", dir=destination.parent) as raw:
        stage = Path(raw)
        for row in rows:
            target = stage / row["name"]
            shutil.copytree(row["source"], target)
            if _tree_hash(target, _tree_files(target)) != row["sha256"]:
                raise InstallerError(f"コピー中にスキルが変更されました: {row['name']}")
        _publish(stage, destination, names)
    return [{**row, "copied_path": str(destination / row["name"])} for row in rows]


def copy_selected_skills(source: Path, names: list[str], destination: Path) -> list[dict[str, Any]]:
    """Copy selected skill directories, including every reference and asset."""
    return _copy_skills(select_skills(source, names), destination)


def export_skill(source: Path, name: str, destination: Path) -> dict[str, Any]:
    """Explicitly export one dormant skill to destination/name without overwrite."""
    row = _skill_metadata(_skill_root(source), _name(name))
    return _copy_skills([row], destination)[0]


def _persona_root(source: Path) -> Path:
    source = Path(source).expanduser().resolve()
    for root in (source / "packs" / "personas", source / "personas"):
        if root.is_symlink():
            raise InstallerError(f"DAパックにsymlinkは使用できません: {root}")
        if root.is_dir():
            return root
    return source / "packs" / "personas"


def _validate_persona(source: Path, value: object) -> dict[str, str]:
    """Use the selected release's validator and restore the caller's imports."""
    source = Path(source).expanduser().resolve()
    plugin = next((root for root in (source / "plugins" / "kiseki-da", source)
                   if (root / "core" / "ctx" / "persona.py").is_file()), None)
    if plugin is None:
        raise InstallerError(f"DA設定のruntime validatorがありません: {source}")
    saved_modules = {key: value for key, value in sys.modules.items()
                     if key == "core" or key.startswith("core.")}
    old_path = list(sys.path)
    old_bytecode = sys.dont_write_bytecode
    try:
        for key in saved_modules:
            del sys.modules[key]
        sys.path.insert(0, str(plugin))
        sys.dont_write_bytecode = True
        module = importlib.import_module("core.ctx.persona")
        try:
            return module.validate_persona(value)
        except module.UserError as exc:
            raise InstallerError(str(exc)) from None
    finally:
        for key in list(sys.modules):
            if key == "core" or key.startswith("core."):
                del sys.modules[key]
        sys.modules.update(saved_modules)
        sys.path[:] = old_path
        sys.dont_write_bytecode = old_bytecode


def _read_persona(source: Path, path: Path) -> dict[str, str]:
    if path.is_symlink():
        raise InstallerError(f"DA設定にsymlinkは使用できません: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError) as exc:
        raise InstallerError(f"DA設定を読めません: {path}: {exc}") from None
    if isinstance(value, dict) and "persona" in value:
        value = value["persona"]
    if not isinstance(value, dict):
        raise InstallerError("DA設定はJSONオブジェクトが必要です。")
    return _validate_persona(source, value)


def get_persona(source: Path, selector: str | Path) -> dict[str, str]:
    """Read a preset ID or an explicitly supplied JSON file without saving it."""
    if isinstance(selector, Path) or str(selector).endswith(".json") or "/" in str(selector) or "\\" in str(selector):
        path = Path(selector).expanduser().absolute()
    else:
        path = _persona_root(source) / (_name(selector) + ".json")
    return _read_persona(source, path)


def list_personas(source: Path) -> list[dict[str, Any]]:
    """Return editable presets as data; the selected runtime validates each one."""
    rows = []
    for path in sorted(_persona_root(source).glob("*.json")):
        _name(path.stem)
        rows.append({
            "id": path.stem, "persona": _read_persona(source, path),
            "source": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        })
    return rows


def copy_pack(source: Path, destination: Path) -> dict[str, Any]:
    """Bundle the entire dormant corpus and preset files outside host discovery."""
    rows = skill_catalog(source)
    personas = list_personas(source)
    destination = _check_destination(destination, ["skills", "personas"])
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".kiseki-pack-", dir=destination.parent) as raw:
        stage = Path(raw)
        _copy_skills(rows, stage / "skills")
        (stage / "personas").mkdir()
        for row in personas:
            target = stage / "personas" / (row["id"] + ".json")
            shutil.copy2(row["source"], target)
            if hashlib.sha256(target.read_bytes()).hexdigest() != row["sha256"]:
                raise InstallerError(f"コピー中にDA設定が変更されました: {row['id']}")
        _publish(stage, destination, ["skills", "personas"])
    return {
        "skills": [{**row, "copied_path": str(destination / "skills" / row["name"])} for row in rows],
        "personas": [{**row, "copied_path": str(destination / "personas" / (row["id"] + ".json"))}
                     for row in personas],
    }
