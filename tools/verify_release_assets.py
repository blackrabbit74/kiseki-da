#!/usr/bin/env python3
"""Verify candidate archive hashes, paths, and tracked-file contents."""
from __future__ import annotations

import hashlib
import json
import posixpath
from pathlib import Path, PurePosixPath
import subprocess
import tarfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tracked() -> dict[str, str]:
    result = subprocess.run(
        ["git", "ls-tree", "-r", "-z", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    )
    entries = [item.decode("utf-8").split("\t", 1) for item in result.stdout.split(b"\0") if item]
    hashes: dict[str, str] = {}
    links: dict[str, str] = {}
    for metadata, path in entries:
        blob = subprocess.run(
            ["git", "show", f"HEAD:{path}"], cwd=ROOT, capture_output=True, check=True,
        ).stdout
        if metadata.startswith("120000 "):
            target = posixpath.normpath(posixpath.join(posixpath.dirname(path), blob.decode("utf-8")))
            if target.startswith(("/", "../")) or target == "..":
                raise ValueError(f"marketplace外のsymlink: {path}")
            links[path] = target
        else:
            hashes[path] = hashlib.sha256(blob).hexdigest()
    originals = dict(hashes)
    for path, target in links.items():
        if target in originals:
            hashes[path] = originals[target]
        else:
            contents = {path + name[len(target):]: digest for name, digest in originals.items()
                        if name.startswith(target + "/")}
            if not contents:
                raise ValueError(f"実体化できないsymlink: {path}")
            hashes.update(contents)
    return hashes


def _relative(name: str, prefix: str) -> str:
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or not path.parts or path.parts[0] != prefix:
        raise ValueError(f"archive pathが不正です: {name}")
    return PurePosixPath(*path.parts[1:]).as_posix()


def _zip_files(path: Path, prefix: str) -> dict[str, str]:
    files: dict[str, str] = {}
    with zipfile.ZipFile(path) as bundle:
        for item in bundle.infolist():
            rel = _relative(item.filename, prefix)
            mode = item.external_attr >> 16
            if (mode & 0o170000) == 0o120000:
                raise ValueError(f"ZIP内にsymlinkがあります: {item.filename}")
            if not item.is_dir():
                files[rel] = hashlib.sha256(bundle.read(item)).hexdigest()
    return files


def _tar_files(path: Path, prefix: str) -> dict[str, str]:
    files: dict[str, str] = {}
    with tarfile.open(path, "r:gz") as bundle:
        for item in bundle.getmembers():
            rel = _relative(item.name, prefix)
            if item.issym() or item.islnk():
                raise ValueError(f"tar内にlinkがあります: {item.name}")
            if item.isfile():
                stream = bundle.extractfile(item)
                if stream is None:
                    raise ValueError(f"tar memberを展開できません: {item.name}")
                files[rel] = hashlib.sha256(stream.read()).hexdigest()
    return files


def verify() -> dict:
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    prefix = f"kiseki-da-{version}"
    archives = {
        f"kiseki-da-{version}.zip": _zip_files,
        f"kiseki-da-{version}.tar.gz": _tar_files,
    }
    expected_sums: dict[str, str] = {}
    for line in (DIST / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) == 2:
            expected_sums[Path(parts[1].lstrip("*")).name] = parts[0].casefold()
    tracked = _tracked()
    checked: list[dict[str, object]] = []
    for name, reader in archives.items():
        path = DIST / name
        actual_hash = _sha256(path)
        if expected_sums.get(name) != actual_hash:
            raise ValueError(f"SHA256SUMS不一致: {name}")
        contents = reader(path, prefix)
        if contents != tracked:
            missing = sorted(set(tracked) - set(contents))
            extra = sorted(set(contents) - set(tracked))
            changed = sorted(path for path in set(contents) & set(tracked)
                             if contents[path] != tracked[path])
            raise ValueError(
                f"tracked content不一致: {name}: missing={missing[:5]} extra={extra[:5]} changed={changed[:5]}"
            )
        checked.append({"name": name, "sha256": actual_hash, "files": len(contents)})
    return {"ok": True, "version": version, "tracked_files": len(tracked), "archives": checked}


def main() -> int:
    try:
        print(json.dumps(verify(), ensure_ascii=False, indent=2))
    except (OSError, ValueError, zipfile.BadZipFile, tarfile.TarError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
