"""Check a release manifest against local bytes and recorded channel evidence.

The JSON manifest is an explicit, reviewed companion to DEPLOY_CONTRACT.md. This
tool never publishes or treats a receipt string as independent remote proof.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

HEX256 = re.compile(r"[0-9a-f]{64}\Z")
COMMIT = re.compile(r"[0-9a-f]{40}\Z")
CHANNEL_MARKER = re.compile(r"<!--\s*deploy-required-channels:\s*(\[[\s\S]*?\])\s*-->")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                            text=True, check=False)
    if result.returncode:
        raise ValueError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def inside(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ValueError(f"expected a project-relative path: {relative!r}")
    target = (root / relative).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError(f"path escapes project: {relative}")
    return target


def _unique(items: list[dict], label: str, errors: list[str]) -> None:
    names = [item.get("name") for item in items]
    if any(not isinstance(name, str) or not name.strip() for name in names):
        errors.append(f"{label} needs a nonempty name")
    valid = [name for name in names if isinstance(name, str)]
    if len(valid) != len(set(valid)):
        errors.append(f"{label} names must be unique")


def contract_channels(contract: Path) -> list[str] | None:
    match = CHANNEL_MARKER.search(contract.read_text(encoding="utf-8"))
    if not match:
        return None
    names = json.loads(match[1])
    if not isinstance(names, list) or not names or any(
        not isinstance(name, str) or not name.strip() for name in names
    ) or len(names) != len(set(names)):
        raise ValueError("deploy-required-channels marker must be a unique JSON string list")
    return names


def check(root: Path, manifest_path: Path, mode: str) -> dict:
    root = root.resolve()
    manifest_path = manifest_path.resolve()
    if manifest_path.is_relative_to(root):
        raise ValueError("manifest must be outside the source repository to avoid a self-referential source commit")
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    artifact_root = Path(data.get("artifact_root", str(root))).resolve()
    errors: list[str] = []
    warnings: list[str] = []
    if data.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    version = data.get("version")
    if not isinstance(version, str) or not version.strip():
        errors.append("version is missing")
    try:
        head = git(root, "rev-parse", "HEAD")
        dirty = bool(git(root, "status", "--porcelain"))
    except ValueError as exc:
        head, dirty = None, True
        errors.append(str(exc))
    if not COMMIT.fullmatch(str(data.get("source_commit", ""))):
        errors.append("source_commit must be a full Git commit hash")
    elif head and data["source_commit"] != head:
        errors.append("source_commit differs from Git HEAD")
    if dirty:
        (errors if mode == "publish" else warnings).append("source tree is dirty")

    contract = root / "DEPLOY_CONTRACT.md"
    if not contract.is_file():
        errors.append("DEPLOY_CONTRACT.md is missing")
    elif data.get("contract_sha256") != sha256(contract):
        errors.append("deployment contract changed since manifest was prepared")
    required_by_contract = None
    if contract.is_file():
        try:
            required_by_contract = contract_channels(contract)
        except (ValueError, json.JSONDecodeError) as exc:
            errors.append(str(exc))
        if required_by_contract is None:
            warnings.append("contract lacks deploy-required-channels marker; check channel completeness against its prose")

    artifacts = data.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        errors.append("artifacts must be a nonempty list")
        artifacts = []
    elif any(not isinstance(entry, dict) for entry in artifacts):
        errors.append("artifact entries must be objects")
        artifacts = [entry for entry in artifacts if isinstance(entry, dict)]
    artifact_paths: set[str] = set()
    for entry in artifacts:
        path = entry.get("path")
        if not isinstance(path, str):
            errors.append("artifact path must be a string")
            continue
        if path in artifact_paths:
            errors.append(f"duplicate artifact: {path}")
        artifact_paths.add(path)
        if entry.get("version") != version:
            errors.append(f"artifact version differs: {path}")
        if not HEX256.fullmatch(str(entry.get("sha256", ""))):
            errors.append(f"artifact needs a SHA-256 hash: {path}")
        try:
            target = inside(artifact_root, path)
            if not target.is_file():
                errors.append(f"artifact missing: {path}")
            elif entry.get("sha256") != sha256(target):
                errors.append(f"artifact hash differs: {path}")
        except ValueError as exc:
            errors.append(str(exc))

    surfaces = data.get("surfaces")
    if not isinstance(surfaces, list) or not surfaces:
        errors.append("surfaces must be a nonempty list")
        surfaces = []
    else:
        if any(not isinstance(item, dict) for item in surfaces):
            errors.append("surface entries must be objects")
            surfaces = [item for item in surfaces if isinstance(item, dict)]
        _unique(surfaces, "surface", errors)
    for item in surfaces:
        if item.get("version") != version:
            errors.append(f"surface version differs: {item.get('name')}")
        if not isinstance(item.get("artifact"), str) or item.get("artifact") not in artifact_paths:
            errors.append(f"surface artifact is undeclared: {item.get('name')}")

    channels = data.get("channels")
    if not isinstance(channels, list) or not channels:
        errors.append("channels must explicitly list every required destination")
        channels = []
    else:
        if any(not isinstance(item, dict) for item in channels):
            errors.append("channel entries must be objects")
            channels = [item for item in channels if isinstance(item, dict)]
        _unique(channels, "channel", errors)
    if required_by_contract is not None:
        missing = set(required_by_contract) - {item.get("name") for item in channels
                                               if item.get("required") is True}
        if missing:
            errors.append("required contract channels absent or disabled in manifest: " + ", ".join(sorted(missing)))
    for item in channels:
        name = item.get("name")
        if type(item.get("required")) is not bool:
            errors.append(f"channel required flag must be boolean: {name}")
        if item.get("version") != version:
            errors.append(f"channel version differs: {name}")
        if not isinstance(item.get("artifact"), str) or item.get("artifact") not in artifact_paths:
            errors.append(f"channel artifact is undeclared: {name}")
        if mode == "publish" and item.get("required"):
            receipt = item.get("receipt")
            if not isinstance(receipt, dict) or not receipt.get("evidence") or not receipt.get("verified_at"):
                errors.append(f"required channel lacks verification receipt: {name}")
            else:
                try:
                    datetime.fromisoformat(receipt["verified_at"].replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    errors.append(f"channel receipt timestamp is invalid: {name}")
                if receipt.get("artifact_sha256") != next(
                    (a.get("sha256") for a in artifacts if a.get("path") == item.get("artifact")), None
                ):
                    errors.append(f"channel receipt artifact hash differs: {name}")

    return {"schema_version": 1, "mode": mode, "status": "ready" if not errors else "incomplete",
            "version": version, "source_commit": head, "contract": str(contract),
            "contract_sha256": sha256(contract) if contract.is_file() else None,
            "manifest": str(manifest_path), "manifest_sha256": sha256(manifest_path),
            "artifacts": artifacts, "surfaces": surfaces, "channels": channels,
            "errors": errors, "warnings": warnings,
            "note": "Channel receipts are recorded evidence, not independent remote verification."}


def init(root: Path, output: Path, version: str, artifact_names: list[str],
         surface_names: list[str], channel_names: list[str],
         artifact_root: Path | None = None) -> dict:
    root = root.resolve()
    artifact_root = (artifact_root or root).resolve()
    contract = root / "DEPLOY_CONTRACT.md"
    if not contract.is_file():
        raise ValueError("DEPLOY_CONTRACT.md is missing")
    if not channel_names:
        channel_names = contract_channels(contract) or []
    if not artifact_names or not surface_names or not channel_names:
        raise ValueError("name at least one artifact, surface and channel explicitly")
    if len(set(artifact_names)) != len(artifact_names):
        raise ValueError("artifact paths must be unique")
    artifacts = []
    for name in artifact_names:
        target = inside(artifact_root, name)
        if not target.is_file():
            raise ValueError(f"artifact missing: {name}")
        artifacts.append({"path": name, "sha256": sha256(target), "version": version})
    return {"schema_version": 1, "version": version, "artifact_root": str(artifact_root),
            "source_commit": git(root, "rev-parse", "HEAD"),
            "contract_sha256": sha256(contract), "artifacts": artifacts,
            "surfaces": [{"name": name, "version": version, "artifact": artifact_names[0]}
                         for name in surface_names],
            "channels": [{"name": name, "required": True, "version": version,
                          "artifact": artifact_names[0], "receipt": None} for name in channel_names]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    start = sub.add_parser("init", help="write an explicit manifest starting from real local bytes")
    start.add_argument("--root", type=Path, required=True)
    start.add_argument("--output", type=Path, required=True)
    start.add_argument("--version", required=True)
    start.add_argument("--artifact-root", type=Path,
                       help="Release-set directory holding artifact paths; defaults to the source repository")
    start.add_argument("--artifact", action="append", required=True)
    start.add_argument("--surface", action="append", required=True)
    start.add_argument("--channel", action="append", default=[],
                       help="repeat for each channel; optional if contract has deploy-required-channels marker")
    verify = sub.add_parser("check", help="check local release and recorded channel receipts")
    verify.add_argument("--root", type=Path, required=True)
    verify.add_argument("--manifest", type=Path, required=True)
    verify.add_argument("--mode", choices=("candidate", "publish"), required=True)
    verify.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.output.resolve().is_relative_to(args.root.resolve()):
            raise ValueError("output must be outside the source repository")
        if args.command == "init":
            result = init(args.root, args.output, args.version, args.artifact, args.surface, args.channel,
                          artifact_root=args.artifact_root)
        else:
            result = check(args.root, args.manifest, args.mode)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
        print(args.output)
        return 0 if result.get("status", "ready") == "ready" else 1
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"release preflight: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
