# PyIncucyte deploy contract

## Release identity

Every release uses one clean source commit and one matching `v<version>` tag.
The version comes from `pyproject.toml`; the frozen application, installer,
wheel, and source distribution must carry the same version. The current
working version is `0.3.1`.

## Required release set

The tag workflow builds and verifies these files outside the checkout:

- one PyIncucyte wheel and one source distribution for Python Package Index;
- `PyIncucyte-<version>-Windows.zip`, a portable one-folder desktop application;
- `PyIncucyte-<version>-Setup.exe`, a per-user installer for the same folder;
- `release-manifest.json`, `SHA256SUMS`, and release notes.

The Windows files are public release assets on `Jay2owe/PyIncucyte`; the wheel
and source distribution are published to the `PyIncucyte` project on Python
Package Index. The executable is never committed to Git and a file left in
local `dist/` is not a release.

## One parity run

The release builder runs the full test suite once, installs the built wheel in a
throwaway environment, imports the package and GUI, freezes the GUI, runs the
frozen application's instrument-free self-test, builds the portable ZIP and
installer, then runs the installed application's self-test before uninstalling
it. The manifest records every gate and every artifact hash. A release with a
skipped installer or failed parity gate cannot be published.

The GUI self-test checks the package version and Tkinter import without opening
a window; the existing fake-device tests cover the instrument-free application
workflow. No instrument address, credential, or acquisition data may enter a
release.

The frozen entry point retains `--scheduled-cli` for Windows Task Scheduler;
the standalone GUI remains the default when no argument is supplied.

## Publication order

1. Push the clean source commit and exact `v<version>` tag.
2. Let `.github/workflows/release.yml` build and verify one release set on
   Windows.
3. Stage the exact wheel, source distribution, portable ZIP, installer,
   manifest, checksums, and notes on the draft GitHub release.
4. Copy only the wheel and source distribution into a clean Python Package
   Index upload directory; publish from that directory and verify their hashes.
5. Publish the GitHub release only after the Python and Windows files still
   match the local manifest.

The Python Package Index upload directory must contain exactly one wheel and one
source distribution. It must not contain the release manifest, checksums, notes,
Windows directory, installer, or nested version directory. First-time GitHub
OpenID Connect trusted publishing uses the exact repository, `release.yml`
workflow filename, and `pypi` environment.

Never rebuild or replace a published version under the same tag. If a channel
fails, keep the release incomplete and resume from the retained release set.

## Candidate command

```powershell
cd "C:\Users\Owner\UK Dementia Research Institute Dropbox\Brancaccio Lab\Jamie\Experiments\PyIncucyte"
python scripts/build_release.py --out C:\PyIncucyte-Releases --allow-dirty
```

The candidate command stops before publication.
