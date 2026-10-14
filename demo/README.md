# Offline acquisition example

Status: verified headless; every exported pixel matches the fixed analytic fixture. The image viewer is available with `--show`.

From this checkout, run `python demo/run_demo.py`. It generates tiny deterministic input, uses the real public client, exports a TIFF and checks every pixel with zero tolerance. `python demo/run_demo.py --show` opens the actual image viewer. Real sources and settings are isolated; temporary output is removed on exit.

[Expected answers](expected_result.json) describe analytic pixel values, not biological measurements. Explicitly approving changed answers requires `python demo/run_demo.py --update-expected --reason "explanation"`; this records the reason and must be reviewed alongside the fixture changes. Ordinary runs never update expected answers.

[Verification and performance review](../docs/software-performance/README.md) records the broader app checks. Fixture generators live in tests/; no external acquisition or network connection is needed.

## Desktop development

Run `python demo/open_app.py --reload` to open the actual application on isolated synthetic data and restart it after source edits. Closing the window stops the launcher. `python demo/open_app.py --check` opens the populated desktop and closes it automatically for verification. Both populated-desktop check commands passed in the current review.
