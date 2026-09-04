#!/usr/bin/env python3
"""Build reproducible release archives from tracked files only."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import subprocess
import sys

from publication_audit import audit


ROOT = Path(__file__).resolve().parents[1]


def _run(args: list[str], *, stdout=None) -> None:
    subprocess.run(args, cwd=ROOT, stdout=stdout, check=True)


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
    with archives[0].open("wb") as stream:
        _run(["git", "archive", "--format=zip", f"--prefix={prefix}", "HEAD"], stdout=stream)
    with archives[1].open("wb") as stream:
        _run(["git", "archive", "--format=tar.gz", f"--prefix={prefix}", "HEAD"], stdout=stream)
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
