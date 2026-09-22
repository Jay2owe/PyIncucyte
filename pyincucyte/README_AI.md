# PyIncucyte AI context

# PyIncucyte overview

PyIncucyte asks an Incucyte instrument what vessels and scans exist, previews selected wells, plans downloads, and writes ImageJ-compatible TIFFs with a manifest.

The agent control boundary is headless and JSON-based. Use `probe_device`, `list_vessels`, `find_vessels`, or `find_scans` to ground identity; use `plan_download` before writing; then use `download` or `watch_once`. `preview` and `protocol` are read-only inspection workflows.

The runner can use a saved login, or an explicit `host` in request parameters. It never asks for a password through JSON. Login remains an existing CLI or GUI operation. The runner request's top-level `root` is an optional disposable credential-store directory for tests or isolated profiles, not an image source.

Download and watch actions write only the requested output folder, its manifest/index, cache, and resume ledger.

## Topics

- `connect-and-discover` — Connect and identify a vessel: Check the instrument, list vessels, and resolve the exact plate before planning.
- `overview` — PyIncucyte overview: Inspect, preview, plan, and download live-cell images from an Incucyte instrument.
- `plan-and-download` — Plan and download images: Preview output count and bytes before writing a resumable download.
- `preview` — Preview wells and channels: Fetch bounded thumbnails to check a vessel, well selection, channel, or processing recipe.
- `protocol` — Read the acquisition protocol: Inspect the plate layout, channels, exposure/stare settings, cadence, and progress.
- `troubleshooting` — PyIncucyte troubleshooting: Recognise common login, host, scan, output, and selection problems.
- `watch-once` — Download new scans once: Run one resumable poll for a scheduler or repeated agent call without leaving a worker running.

## Public topics

- `connect-and-discover` — Connect and identify a vessel: Check the instrument, list vessels, and resolve the exact plate before planning.
- `overview` — PyIncucyte overview: Inspect, preview, plan, and download live-cell images from an Incucyte instrument.
- `plan-and-download` — Plan and download images: Preview output count and bytes before writing a resumable download.
- `preview` — Preview wells and channels: Fetch bounded thumbnails to check a vessel, well selection, channel, or processing recipe.
- `protocol` — Read the acquisition protocol: Inspect the plate layout, channels, exposure/stare settings, cadence, and progress.
- `troubleshooting` — PyIncucyte troubleshooting: Recognise common login, host, scan, output, and selection problems.
- `watch-once` — Download new scans once: Run one resumable poll for a scheduler or repeated agent call without leaving a worker running.

Read the structured `pyincucyte_context.json` artifact or use `from pyincucyte import context` for topic reads and search.
