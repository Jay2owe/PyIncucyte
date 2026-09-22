"""Public, read-only usage context for PyIncucyte.

Reading or searching this module does not contact an instrument, construct a
client, load credentials, start a watcher, or import the GUI.
"""
from __future__ import annotations

from difflib import get_close_matches
import re
from typing import Any

PACKAGE = "pyincucyte"
VERSION = "0.3.1"
READER_CONTRACT = {
    "python": "from pyincucyte import context; context.read(topic=None, format='text')",
    "search": "context.search(query, limit=5)",
    "runner": "context [topic] or context --search <query>",
    "read_only": True,
}

_TOPICS: dict[str, dict[str, Any]] = {
    "overview": {
        "title": "PyIncucyte overview",
        "description": "Inspect, preview, plan, and download live-cell images from an Incucyte instrument.",
        "keywords": ["Incucyte", "vessel", "plate", "scan", "agent", "actions"],
        "prerequisites": [],
        "related": ["connect-and-discover", "plan-and-download", "troubleshooting"],
        "content": """PyIncucyte asks an Incucyte instrument what vessels and scans exist, previews selected wells, plans downloads, and writes ImageJ-compatible TIFFs with a manifest.

The agent control boundary is headless and JSON-based. Use `probe_device`, `list_vessels`, `find_vessels`, or `find_scans` to ground identity; use `plan_download` before writing; then use `download` or `watch_once`. `preview` and `protocol` are read-only inspection workflows.

The runner can use a saved login, or an explicit `host` in request parameters. It never asks for a password through JSON. Login remains an existing CLI or GUI operation. The runner request's top-level `root` is an optional disposable credential-store directory for tests or isolated profiles, not an image source.

Download and watch actions write only the requested output folder, its manifest/index, cache, and resume ledger.""",
    },
    "connect-and-discover": {
        "title": "Connect and identify a vessel",
        "description": "Check the instrument, list vessels, and resolve the exact plate before planning.",
        "keywords": ["probe", "host", "login", "credentials", "vessels", "find", "plate", "owner"],
        "prerequisites": ["overview"],
        "related": ["plan-and-download", "troubleshooting"],
        "content": """The machine must already have a saved PyIncucyte login, or the request must provide the instrument `host`. Use the existing `pyincucyte login` command or GUI for credential setup; do not put passwords in an agent request.

```python
from pyincucyte import IncucyteClient

with IncucyteClient.from_saved("incucyte.example") as incucyte:
    print(incucyte.probe())
    for vessel in incucyte.find_vessels(name="Cry1"):
        print(vessel.to_dict())
```

Use `find_scans` when the question is about usable image-bearing scans rather than vessel metadata. IDs and scan times returned by discovery are the only identifiers to pass to later actions; do not infer them from a plate label.""",
    },
    "plan-and-download": {
        "title": "Plan and download images",
        "description": "Preview output count and bytes before writing a resumable download.",
        "keywords": ["plan", "download", "fetch", "output", "wells", "channels", "layout", "manifest", "TIFF"],
        "prerequisites": ["connect-and-discover"],
        "related": ["watch-once", "troubleshooting"],
        "content": """A plan asks for metadata and calculates output files, axes, scan times, selected wells/channels, and estimated bytes. It does not write image files.

```python
from pyincucyte import ExportOptions, IncucyteClient

options = ExportOptions(
    host="incucyte.example",
    output="./plate-38",
    vessels=[38],
    wells="A1-D6",
    channels="phase,green",
    layout="time_stack",
    start_from="first",
)
with IncucyteClient.from_saved(options.host) as incucyte:
    plan = incucyte.plan(options)
    print(plan.to_dict())
    result = incucyte.fetch(options)
    print(result.to_dict())
```

Layouts are `separate` (one image per well/channel/time), `channel_stack`, `time_stack`, and `time_channel_stack`. Choose the layout from the downstream axes requirement, not from filename preference. A successful result reports files, bytes, manifest path, and errors. Repeating the same recipe uses the resume ledger and source cache where configured.""",
    },
    "preview": {
        "title": "Preview wells and channels",
        "description": "Fetch bounded thumbnails to check a vessel, well selection, channel, or processing recipe.",
        "keywords": ["preview", "thumbnail", "well", "channel", "contrast", "calibrate", "unmix", "background"],
        "prerequisites": ["connect-and-discover"],
        "related": ["plan-and-download", "protocol"],
        "content": """Use `preview` before downloading when you need to verify that the selected vessel, wells, channels, or processing recipe is correct. The structured result contains thumbnail metadata and errors; it does not replace quantitative analysis.

```python
with IncucyteClient.from_saved("incucyte.example") as incucyte:
    previews = incucyte.preview(vessel=38, wells="A1-B3", channels="phase")
    print(previews.to_dict())
```

`calibrate`, `background`, and `unmix` use the same recipe vocabulary as downloads. Treat display contrast as a recognition aid. Use the result's reported wells and channel names to confirm the request before a write.""",
    },
    "protocol": {
        "title": "Read the acquisition protocol",
        "description": "Inspect the plate layout, channels, exposure/stare settings, cadence, and progress.",
        "keywords": ["protocol", "exposure", "stare", "wells", "cadence", "progress", "SVG"],
        "prerequisites": ["connect-and-discover"],
        "related": ["preview", "troubleshooting"],
        "content": """`protocol` reads metadata and scan information without downloading image pixels. It reports the requested acquisition design separately from the achieved interval and current progress.

```python
with IncucyteClient.from_saved("incucyte.example") as incucyte:
    protocol = incucyte.protocol(vessel=38, scan=False)
    print(protocol.to_dict())
    protocol.save("./vessel-38-protocol.svg")
```

Use `scan=False` for a fast plan-only description. Use the default scan-aware form when achieved cadence or live status matters.""",
    },
    "watch-once": {
        "title": "Download new scans once",
        "description": "Run one resumable poll for a scheduler or repeated agent call without leaving a worker running.",
        "keywords": ["watch", "once", "poll", "resume", "ledger", "batch", "live"],
        "prerequisites": ["plan-and-download"],
        "related": ["troubleshooting"],
        "content": """Use `watch_once` when another scheduler or automation system will invoke PyIncucyte repeatedly. It performs one poll, applies the configured time window and batching rule, writes eligible new scans, and returns. It does not leave a resident process running.

```python
with IncucyteClient.from_saved("incucyte.example") as incucyte:
    result = incucyte.watch_once(
        vessel=38,
        output="./plate-38",
        channels="phase,green",
        batch_after="7d",
    )
    print(result.to_dict())
```

A held batch is a normal outcome: no files should be written until the frame-count or age rule is met. Check `file_count`, `errors`, and `device_status` before deciding whether another call is needed.""",
    },
    "troubleshooting": {
        "title": "PyIncucyte troubleshooting",
        "description": "Recognise common login, host, scan, output, and selection problems.",
        "keywords": ["HostNotSetError", "NotLoggedInError", "DeviceUnreachableError", "VesselNotFoundError", "no scan", "output", "error"],
        "prerequisites": ["overview"],
        "related": ["connect-and-discover", "plan-and-download", "watch-once"],
        "content": """If the runner reports `HostNotSetError`, pass an explicit `host` or select a saved device. If it reports `NotLoggedInError`, complete the existing login workflow on that machine and retry `probe_device`; do not send a password through JSON.

If the device is unreachable, check the internal network route and rerun `probe_device`. A successful login does not prove the current network route is available.

If a vessel search returns nothing, broaden `find_vessels` by removing optional owner, plate, or channel filters, then use the returned ID. If `find_scans` returns nothing, the vessel may not have a usable image-bearing scan in the requested date window; inspect its first/last scan metadata and widen the window deliberately.

If `plan_download` rejects the request, check that an output folder, at least one vessel, and valid channels/layout are present. If a download returns errors, inspect the per-file errors and manifest path before retrying; a failed call can still have written earlier files.""",
    },
}


def _topic_key(topic: str) -> str:
    return str(topic).strip().lower().replace(" ", "-").replace("_", "-")


def _combined_content(key: str, seen: set[str] | None = None) -> str:
    seen = set() if seen is None else seen
    if key in seen:
        return ""
    seen.add(key)
    entry = _TOPICS[key]
    parts = []
    for prerequisite in entry["prerequisites"]:
        if prerequisite in _TOPICS:
            parts.append(_combined_content(prerequisite, seen))
    parts.append(entry["content"])
    return "\n\n".join(part for part in parts if part)


def _structured(key: str) -> dict[str, Any]:
    entry = _TOPICS[key]
    return {
        "ok": True,
        "package": PACKAGE,
        "version": VERSION,
        "topic": key,
        "title": entry["title"],
        "description": entry["description"],
        "content": _combined_content(key),
        "prerequisites": list(entry["prerequisites"]),
        "related_topics": list(entry["related"]),
    }


def read(topic: str | None = None, *, format: str = "text") -> Any:
    """Read the overview or one named public usage topic."""
    if format not in {"text", "json"}:
        return {"ok": False, "error": "format must be 'text' or 'json'"}
    requested_default = topic is None
    key = _topic_key(topic or "overview")
    if key not in _TOPICS:
        suggestions = get_close_matches(key, _TOPICS, n=3, cutoff=0.35)
        result = {"ok": False, "package": PACKAGE, "version": VERSION,
                  "topic": key, "error": "Unknown topic", "suggestions": suggestions}
        return result if format == "json" else (
            f"Unknown PyIncucyte context topic {topic!r}. "
            f"Try: {', '.join(suggestions or sorted(_TOPICS))}.")
    if format == "json":
        result = _structured(key)
        if requested_default:
            result["topics"] = [
                {"topic": name, "title": entry["title"],
                 "description": entry["description"]}
                for name, entry in sorted(_TOPICS.items())
            ]
        return result
    entry = _TOPICS[key]
    text = f"# {entry['title']}\n\n{_combined_content(key)}"
    if requested_default:
        text += "\n\n## Topics\n\n" + "\n".join(
            f"- `{name}` — {item['title']}: {item['description']}"
            for name, item in sorted(_TOPICS.items())
        )
    return text


def search(query: str, *, limit: int = 5) -> dict[str, Any]:
    """Search public topics using titles, descriptions, keywords, and text."""
    if not isinstance(query, str) or not query.strip():
        return {"ok": True, "query": query, "results": []}
    words = set(re.findall(r"[a-z0-9_.-]+", query.lower()))
    scored = []
    for key, entry in _TOPICS.items():
        haystack = " ".join([
            entry["title"], entry["description"], " ".join(entry["keywords"]),
            entry["content"], key,
        ]).lower()
        score = sum(3 if word in entry["title"].lower() else 1
                    for word in words if word in haystack)
        if score:
            scored.append((score, key, entry))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return {"ok": True, "query": query, "results": [
        {"topic": key, "title": entry["title"],
         "description": entry["description"]}
        for _score, key, entry in scored[:max(0, int(limit))]
    ]}


def export_context() -> dict[str, Any]:
    """Return the portable context artifact generated from this module."""
    return {
        "package": PACKAGE,
        "version": VERSION,
        "reader_contract": READER_CONTRACT,
        "topics": [_structured(key) for key in sorted(_TOPICS)],
    }
