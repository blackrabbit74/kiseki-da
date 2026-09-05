#!/usr/bin/env python3
"""Build reproducible release archives from tracked files only."""
from __future__ import annotations

import argparse
import hashlib
import io
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import zipfile
import gzip

from publication_audit import audit


ROOT = Path(__file__).resolve().parents[1]


def _run(args: list[str], *, stdout=None) -> None:
    subprocess.run(args, cwd=ROOT, stdout=stdout, check=True)


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_archives(root: Path, archives: list[Path], prefix: str) -> None:
    """Materialize marketplace links from a tracked snapshot, never the worktree."""
    snapshot = subprocess.run(["git", "archive", "--format=tar", "HEAD"], cwd=root,
                              capture_output=True, check=True).stdout
    with tempfile.TemporaryDirectory(prefix="kiseki-release-") as raw:
        stage = Path(raw).resolve()
        with tarfile.open(fileobj=io.BytesIO(snapshot)) as bundle:
            bundle.extractall(stage, filter="data")
        # Only links to regular tracked trees inside this snapshot are supported.
        links = [p for p in stage.rglob("*") if p.is_symlink()]
        for link in links:
            target = link.resolve(strict=True)
            target.relative_to(stage)
            if target.is_dir() and any(p.is_symlink() for p in target.rglob("*")):
                raise ValueError(f"Nested release symlink: {link.relative_to(stage)}")
            if target == stage or target in link.parents:
                raise ValueError(f"Recursive release symlink: {link.relative_to(stage)}")
        def files(directory: Path):
            for path in sorted(directory.iterdir()):
                if path.is_dir():
                    yield from files(path)
                else:
                    yield path
        with zipfile.ZipFile(archives[0], "w", compression=zipfile.ZIP_DEFLATED) as output:
            for path in files(stage):
                info = zipfile.ZipInfo(prefix + path.relative_to(stage).as_posix(), (1980, 1, 1, 0, 0, 0))
                info.external_attr = (0o100755 if path.stat().st_mode & 0o111 else 0o100644) << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                output.writestr(info, path.read_bytes())
        with archives[1].open("wb") as stream, gzip.GzipFile(filename="", fileobj=stream, mode="wb", mtime=0) as gz:
            with tarfile.open(fileobj=gz, mode="w", dereference=True) as output:
                for path in files(stage):
                    info = output.gettarinfo(str(path), prefix + path.relative_to(stage).as_posix())
                    info.uid = info.gid = info.mtime = 0
                    info.uname = info.gname = ""
                    with path.open("rb") as content:
                        output.addfile(info, content)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--publish-ready", action="store_true")
    parser.add_argument("--gates", type=Path)
    args = parser.parse_args(argv)
    result = audit(args.gates)
    if not result["ok"] or (args.publish_ready and not result["release_ready"]):
        for error in result["errors"]:
            print(error, file=sys.stderr)
        for blocker in result.get("release_blockers", []):
            print(f"release gate未完了: {blocker}", file=sys.stderr)
        return 1
    dirty = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, text=True,
                           capture_output=True, check=True).stdout.strip()
    if dirty:
        print("releaseはcleanなGit treeからだけ作成できます", file=sys.stderr)
        return 1
    version = result["version"]
    if args.publish_ready:
        expected_tag = f"v{version}"
        tag = subprocess.run(
            ["git", "rev-parse", "--verify", f"refs/tags/{expected_tag}^{{commit}}"],
            cwd=ROOT, text=True, capture_output=True, check=False,
        )
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=True,
        ).stdout.strip()
        if tag.returncode != 0 or tag.stdout.strip() != head:
            print(f"publish-ready assetにはHEADを指すtag {expected_tag}が必要です", file=sys.stderr)
            return 1
    out = ROOT / "dist"
    out.mkdir(exist_ok=True)
    prefix = f"kiseki-da-{version}/"
    archives = [out / f"kiseki-da-{version}.zip", out / f"kiseki-da-{version}.tar.gz"]
    write_archives(ROOT, archives, prefix)
    sums = out / "SHA256SUMS"
    sums.write_text("".join(f"{_digest(path)}  {path.name}\n" for path in archives), encoding="utf-8")
    marker = out / "CANDIDATE_ONLY.txt"
    if args.publish_ready:
        marker.unlink(missing_ok=True)
    else:
        marker.write_text("公開不可: release gateと利用者承認が未完了です。\n", encoding="utf-8")
    for path in (*archives, sums, *(() if args.publish_ready else (marker,))):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
