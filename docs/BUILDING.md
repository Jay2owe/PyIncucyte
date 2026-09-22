# Building the PyIncucyte desktop application

PyIncucyte is released as a one-folder Windows application, a portable ZIP,
and a per-user Setup executable. The Python package and Windows application are
built from the same source commit and checked for version parity.

Run this from a Windows checkout with Inno Setup 6 installed. Keep the output
outside Dropbox because PyInstaller holds the application files open while it
writes them.

```powershell
python -m pip install -e ".[test,release]"
python scripts/build_release.py --out C:\PyIncucyte-Releases --allow-dirty
```

The release directory contains the wheel, source distribution,
`PyIncucyte-<version>-Windows.zip`, `PyIncucyte-<version>-Setup.exe`, a release
manifest, and SHA-256 checksums. `--allow-dirty` is for local candidates only;
the tag workflow rejects dirty release inputs.

The frozen application opens the GUI with no arguments. `--self-test` checks
the package version and Tkinter import without contacting an instrument, and
`--scheduled-cli` retains the task-scheduler route used by the CLI.
