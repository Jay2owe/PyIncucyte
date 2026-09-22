"""Verify a PyIncucyte release set before publication."""

from __future__ import annotations

import argparse
import hashlib
import json
from urllib.request import urlopen
from pathlib import Path


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("release", type=Path)
    parser.add_argument("--tag")
    parser.add_argument("--commit")
    parser.add_argument("--pypi", action="store_true")
    args = parser.parse_args(argv)
    root = args.release.resolve()
    manifest = json.loads((root / "release-manifest.json").read_text(encoding="utf-8"))
    if args.tag and manifest.get("tag") != args.tag:
        raise SystemExit("release tag mismatch")
    if args.commit and manifest.get("source_commit") != args.commit:
        raise SystemExit("release commit mismatch")
    if manifest.get("tests", {}).get("pytest") != "passed":
        raise SystemExit("pytest gate did not pass")
    for relative, record in manifest["artifacts"].items():
        path = root / relative
        if not path.is_file() or digest(path) != record["sha256"]:
            raise SystemExit(f"artifact hash mismatch: {relative}")
    if args.pypi:
        project = manifest["application"]
        with urlopen(f"https://pypi.org/pypi/{project}/json", timeout=30) as response:
            remote = json.load(response)
        by_name = {item["filename"]: item["digests"]["sha256"] for item in remote["urls"]}
        for relative in manifest["artifacts"]:
            path = root / relative
            if path.suffix in {".whl", ".gz"} and by_name.get(path.name) != digest(path):
                raise SystemExit(f"PyPI hash mismatch: {path.name}")
    print(f"verified {manifest['application']} {manifest['version']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
