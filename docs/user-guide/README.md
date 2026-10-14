# PyIncucyte user guide

Status: current source-checkout guide; publication is separate from this review.

## Start without an instrument

From a source checkout, run `python demo/run_demo.py`. A simulated device supplies a tiny acquisition to the real public client; the demo exports and verifies every pixel. Use `python demo/run_demo.py --show` to inspect it in the real viewer. The simulated transport is explicit; real device credentials, settings and outputs are not used.

## Download a real acquisition

```python
from pyincucyte import IncucyteClient

with IncucyteClient.from_saved() as instrument:
    vessels = instrument.vessels()
    result = instrument.fetch(vessel=vessels[0].id, output="./export")
    print(result.summary())
```

Sign in to the instrument in the desktop application first. Select a vessel, wells, channels and time window; Preview images shows representative data, while Preview download shows the intended export. Download writes the selected data; Sync continues to collect new scans.

Calibration, background subtraction and unmixing use the chosen processing recipe. Changing the desktop theme changes controls, not scientific pixels. Keep the output manifest beside its TIFFs so downstream tools can recover channels, timepoints and provenance.

## Reproduce and resume

The desktop can copy equivalent Python and command-line recipes. Saved presets retain choices, and the download state ledger supports resume. Presets, credentials and desktop settings use atomic replacement so a failed save preserves the previous file.

Use `python -m pyincucyte --help` for command discovery and `pyincucyte.context` for the machine-readable action guide. Live instrument availability and network latency are separate from simulated-device benchmarks.

## Development and evidence

The source checkout's `docs/software-performance/README.md` links the current review, frozen baseline, measurements and verification status. `tests/fakes.py` supplies the simulated device; `demo/expected_result.json` contains the analytic pixel answers. Updating expected answers requires an explicit reason. Ordinary demo runs leave them unchanged.

Run `python scripts/verify.py --structure` for architecture checks and `python -m pytest -q tests/test_performance_contracts.py` for focused checks. Build this guide with `mkdocs build --strict`. Earlier attempts remain indexed in the performance review.

For desktop development, `python demo/open_app.py --reload` opens the app with synthetic input and restarts it on source changes. Close its window to stop.
