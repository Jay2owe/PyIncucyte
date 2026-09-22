#!/usr/bin/env python
"""Second tracked entrypoint for the PyIncucyte headless runner."""
from __future__ import annotations

import runpy
from pathlib import Path


if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).with_name("pyincucyte_runner.py")),
                   run_name="__main__")
