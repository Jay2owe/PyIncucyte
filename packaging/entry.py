"""Frozen entry point for the PyIncucyte desktop app.

PyInstaller runs its entry script as ``__main__`` with no parent package, so
freezing a module that uses relative imports fails on its first line. This shim
imports the package properly and calls into it.
"""

import json
import sys
from pathlib import Path


def run(argv=None):
    """Open the window, or run a scheduled CLI pass from the frozen app."""
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["--self-test"]:
        import tkinter
        import pyincucyte
        import pyincucyte.gui.app

        report = argv[argv.index("--self-test-report") + 1] if "--self-test-report" in argv else None
        payload = {
            "ok": True,
            "application": "PyIncucyte",
            "version": pyincucyte.__version__,
            "gui": "tkinter",
            "tk_version": tkinter.TkVersion,
        }
        if report:
            path = Path(report)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        return 0
    if argv[:1] == ["--version"]:
        from pyincucyte import __version__

        print(f"pyincucyte {__version__}")
        return 0
    if argv[:1] == ["--scheduled-cli"]:
        from pyincucyte.cli import main as cli_main
        return cli_main(argv[1:])
    from pyincucyte.gui import main as gui_main
    return gui_main()

if __name__ == "__main__":
    raise SystemExit(run())
