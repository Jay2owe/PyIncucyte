"""Build one immutable PyIncucyte Python and Windows release set."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import venv
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = "PyIncucyte"
PACKAGE = "pyincucyte"
EXE = "PyIncucyte.exe"
SPEC = ROOT / "packaging" / "pyincucyte.spec"
ISS = ROOT / "packaging" / "pyincucyte.iss"


def run(command, *, cwd=ROOT, env=None):
    print("+", " ".join(map(str, command)))
    subprocess.run([str(x) for x in command], cwd=cwd, env=env, check=True)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def version() -> str:
    import tomllib

    with (ROOT / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)["project"]["version"]


def source_commit() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def ensure_source(*, allow_dirty: bool) -> None:
    if allow_dirty:
        return
    dirty = subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()
    if dirty:
        raise RuntimeError("release input is dirty; commit it or pass --allow-dirty for a candidate")


def write_version_info(path: Path, release_version: str) -> None:
    major, minor, patch = (int(part) for part in release_version.split("."))
    path.write_text(
        "# UTF-8\n"
        "VSVersionInfo(\n"
        "  ffi=FixedFileInfo(filevers=(%d, %d, %d, 0), prodvers=(%d, %d, %d, 0), "
        "mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),\n"
        "  kids=[StringFileInfo([StringTable('040904B0',[StringStruct('CompanyName','Brancaccio Lab'),"
        "StringStruct('FileDescription','PyIncucyte desktop application'),StringStruct('FileVersion','%s'),"
        "StringStruct('ProductName','PyIncucyte'),StringStruct('ProductVersion','%s')])]),"
        "VarFileInfo([VarStruct('Translation',[1033,1200])])])\n" %
        (major, minor, patch, major, minor, patch, release_version, release_version),
        encoding="utf-8",
    )


def clean_install_smoke(wheel: Path, release_version: str, build_root: Path) -> dict:
    venv_dir = build_root / "wheel-smoke-venv"
    venv.EnvBuilder(with_pip=True).create(venv_dir)
    python = venv_dir / "Scripts" / "python.exe"
    run([python, "-m", "pip", "install", "--disable-pip-version-check", str(wheel)], cwd=build_root)
    report = build_root / "wheel-smoke-report.json"
    code = (
        "import json,sys; import pyincucyte; import pyincucyte.gui.app; "
        "assert pyincucyte.__version__ == sys.argv[1]; "
        "json.dump({'ok': True, 'application': 'PyIncucyte', 'version': pyincucyte.__version__}, "
        "open(sys.argv[2], 'w', encoding='utf-8'))"
    )
    run([python, "-c", code, release_version, report], cwd=build_root)
    return json.loads(report.read_text(encoding="utf-8"))


def find_iscc() -> str:
    configured = os.environ.get("ISCC_EXE")
    if configured and Path(configured).is_file():
        return configured
    for candidate in ("ISCC.exe", "iscc"):
        found = shutil.which(candidate)
        if found:
            return found
    raise RuntimeError("Inno Setup 6 compiler not found; install it or pass ISCC_EXE")


def installer_smoke(installer: Path, build_root: Path) -> None:
    install_dir = build_root / "installed-app"
    run([installer, "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART",
         "/CURRENTUSER", f"/DIR={install_dir}"], cwd=build_root)
    installed_exe = install_dir / EXE
    if not installed_exe.is_file():
        raise RuntimeError("installer did not create the application executable")
    report = build_root / "installed-smoke-report.json"
    run([installed_exe, "--self-test", "--self-test-report", report], cwd=build_root)
    data = json.loads(report.read_text(encoding="utf-8"))
    if data.get("version") != version():
        raise RuntimeError("installed application version differs from package version")
    uninstaller = install_dir / "unins000.exe"
    if not uninstaller.is_file():
        raise RuntimeError("installer did not create an uninstaller")
    run([uninstaller, "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"], cwd=build_root)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--tag")
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument("--skip-installer", action="store_true")
    args = parser.parse_args(argv)

    release_version = version()
    if args.tag and args.tag != f"v{release_version}":
        raise RuntimeError(f"tag {args.tag} does not match package version {release_version}")
    ensure_source(allow_dirty=args.allow_dirty)
    out = args.out.resolve()
    if out.is_relative_to(ROOT):
        raise RuntimeError("release output must be outside the Dropbox checkout")
    release_dir = out / release_version
    if release_dir.exists():
        raise RuntimeError(f"release output already exists: {release_dir}")
    release_dir.mkdir(parents=True)
    build_root = Path(tempfile.mkdtemp(prefix="pyincucyte-release-"))
    try:
        run([sys.executable, "-m", "pytest", "-q"])
        run([sys.executable, "-m", "build", "--outdir", release_dir])
        wheels = sorted(release_dir.glob("*.whl"))
        sdists = sorted(release_dir.glob("*.tar.gz"))
        if len(wheels) != 1 or len(sdists) != 1:
            raise RuntimeError("expected exactly one wheel and one source distribution")
        wheel_report = clean_install_smoke(wheels[0], release_version, build_root)

        version_file = build_root / "version_info.txt"
        write_version_info(version_file, release_version)
        frozen = build_root / "frozen"
        work = build_root / "pyinstaller-work"
        env = dict(os.environ, PYINCUCYTE_VERSION_INFO=str(version_file))
        run([sys.executable, "-m", "PyInstaller", str(SPEC), "--noconfirm", "--clean",
             "--distpath", frozen, "--workpath", work], env=env)
        app_dir = frozen / APP
        app_exe = app_dir / EXE
        if not app_exe.is_file():
            raise RuntimeError(f"PyInstaller did not produce {app_exe}")
        frozen_report = build_root / "frozen-smoke-report.json"
        run([app_exe, "--self-test", "--self-test-report", frozen_report], cwd=build_root)
        frozen_data = json.loads(frozen_report.read_text(encoding="utf-8"))
        if frozen_data.get("version") != release_version:
            raise RuntimeError("frozen application version differs from package version")

        windows = release_dir / "windows"
        windows.mkdir()
        archive = Path(shutil.make_archive(str(windows / f"{APP}-{release_version}-Windows"),
                                           "zip", root_dir=frozen, base_dir=APP))
        installer_status = "skipped"
        if not args.skip_installer:
            iscc = find_iscc()
            installer_dir = build_root / "installer"
            installer_dir.mkdir()
            env = dict(os.environ, PYINCUCYTE_INSTALL_SOURCE_DIR=str(app_dir),
                       PYINCUCYTE_INSTALL_OUTPUT_DIR=str(installer_dir),
                       PYINCUCYTE_INSTALL_VERSION=release_version)
            run([iscc, str(ISS)], env=env)
            installer = installer_dir / f"{APP}-{release_version}-Setup.exe"
            if not installer.is_file():
                raise RuntimeError("Inno Setup did not produce the installer")
            shutil.copy2(installer, windows / installer.name)
            installer_smoke(installer, build_root)
            installer_status = "built"

        notes_path = release_dir / "RELEASE_NOTES.md"
        notes_path.write_text(
            f"# PyIncucyte {release_version}\n\n"
            "This release contains the Python package and the verified Windows desktop application.\n",
            encoding="utf-8",
        )
        artifacts = [*sorted(release_dir.glob("*.whl")), *sorted(release_dir.glob("*.tar.gz")),
                     archive, *sorted(windows.glob("*.exe")), notes_path]
        manifest = {
            "schema": "pyincucyte-release-1",
            "application": APP,
            "version": release_version,
            "source_commit": source_commit(),
            "tag": args.tag,
            "built_utc": datetime.now(timezone.utc).isoformat(),
            "tests": {"pytest": "passed", "wheel_smoke": "passed",
                       "frozen_smoke": "passed", "installer": installer_status},
            "artifacts": {str(path.relative_to(release_dir)).replace("\\", "/"):
                          {"sha256": sha256(path), "bytes": path.stat().st_size}
                          for path in artifacts},
        }
        manifest_path = release_dir / "release-manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        checksum_paths = [manifest_path, *artifacts]
        (release_dir / "SHA256SUMS").write_text(
            "".join(f"{sha256(path)}  {path.relative_to(release_dir).as_posix()}\n" for path in checksum_paths),
            encoding="utf-8",
        )
        print(f"Release assembled: {release_dir}")
        return 0
    finally:
        shutil.rmtree(build_root, ignore_errors=True)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"release build failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
