"""PyIncucyte - download Incucyte live-cell images from Python.

Two ways in.  A desktop app::

    pyincucyte gui                  # or: pyincucyte-gui, python -m pyincucyte.gui

...and an importable API for an automated pipeline::

    from pyincucyte import IncucyteClient

    with IncucyteClient.from_saved() as incucyte:
        result = incucyte.fetch(
            vessel=38, output="./run-01", wells="A1-D6",
            channels="phase,green", layout="time_channel_stack",
            start_from="first")

    for image in result.files:
        segment(image.path, well=image.well, channels=image.channel_names)

``result.files`` carries the well, channel names, timepoints and axis order for
every file, and the same information is written to ``pyincucyte-manifest.json``
next to the images so a later stage can pick up without re-parsing filenames.
"""

import logging

__version__ = "0.3.2"

# A library should not configure logging for its host application; this only
# stops "No handlers could be found" warnings when nobody has set one up.
logging.getLogger("pyincucyte").addHandler(logging.NullHandler())

import importlib as _importlib

_EXPORT_MODULES = {
    "errors": "ApiError AuthenticationError ConfirmationRequiredError DeviceBusyError DeviceUnreachableError HostNotSetError EncryptionUnavailableError ExportCancelled ExportError StackNotExtendable IncucyteError NotLoggedInError TokenExpiredError VesselNotFoundError",
    "models": "DownloadResult ExportPlan LAYOUTS LAYOUT_AXES LAYOUT_DESCRIPTIONS LAYOUT_LABELS OutputFile ProgressEvent Vessel VesselScan human_bytes resolve_layout",
    "device": "DeviceState ScanPattern",
    "options": "ExportOptions",
    "preview": "PreviewImage PreviewSet",
    "protocol": "Protocol Step read_protocol",
    "timeline": "HybridTimelineSource TimelinePreview TimelineSource choose_frames",
    "processing": "Recipe Unmixing",
    "config": "ConfigStore Credentials",
    "state": "StateStore",
    "client": "IncucyteClient",
    "watch": "Watcher",
    "manifest": "load_manifest write_manifest",
    "engine": "DEFAULT_HOST APP_DIR",
}
_LAZY_EXPORTS = {name: module for module, names in _EXPORT_MODULES.items()
                 for name in names.split()}
_LAZY_MODULES = set(_EXPORT_MODULES) | {"channels", "wells", "pyramid", "cache"}


def __getattr__(name):
    if name in _LAZY_MODULES:
        value = _importlib.import_module("." + name, __name__)
        globals()[name] = value
        return value
    module = _LAZY_EXPORTS.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(_importlib.import_module("." + module, __name__), name)
    globals()[name] = value
    return value


def __dir__():
    return sorted(set(globals()) | set(_LAZY_EXPORTS) | _LAZY_MODULES)

# Import names retired in 0.3 - see pyincucyte.compat.
from . import compat  # noqa: E402

compat.install()


def connect(host=None, username=None, password=None, *, store=None, save=True,
            device_name=""):
    """Return a ready client - saved login by default, or fresh credentials."""
    from . import IncucyteClient, DEFAULT_HOST
    if username and password:
        return IncucyteClient.connect(
            host or DEFAULT_HOST, username, password, store=store, save=save,
            device_name=device_name)
    return IncucyteClient.from_saved(host, store=store)


def pull(target=None, *, host=None, username=None, password=None, store=None,
         options=None, out=None, **kwargs):
    """Pull one vessel through a short-lived saved or fresh connection."""
    with connect(host, username, password, store=store) as client:
        return client.pull(target, options, out=out, **kwargs)


def watch_once(target=None, *, host=None, username=None, password=None,
               store=None, options=None, out=None, flush=False, **kwargs):
    """Run one resumable watcher poll without leaving a process resident."""
    with connect(host, username, password, store=store) as client:
        return client.watch_once(
            target, options, out=out, flush=flush, **kwargs)


__all__ = [
    "__version__",
    "connect",
    "pull",
    "watch_once",
    "IncucyteClient",
    "ExportOptions",
    "ExportPlan",
    "DownloadResult",
    "OutputFile",
    "ProgressEvent",
    "Vessel",
    "VesselScan",
    "DeviceState",
    "ScanPattern",
    "PreviewImage",
    "PreviewSet",
    "Protocol",
    "Step",
    "read_protocol",
    "TimelineSource",
    "HybridTimelineSource",
    "TimelinePreview",
    "choose_frames",
    "Recipe",
    "Unmixing",
    "Watcher",
    "StateStore",
    "ConfigStore",
    "Credentials",
    "LAYOUTS",
    "LAYOUT_AXES",
    "LAYOUT_LABELS",
    "LAYOUT_DESCRIPTIONS",
    "resolve_layout",
    "human_bytes",
    "load_manifest",
    "write_manifest",
    "DEFAULT_HOST",
    "APP_DIR",
    "IncucyteError",
    "ApiError",
    "AuthenticationError",
    "NotLoggedInError",
    "TokenExpiredError",
    "DeviceUnreachableError",
    "HostNotSetError",
    "EncryptionUnavailableError",
    "VesselNotFoundError",
    "ExportError",
    "ExportCancelled",
    "StackNotExtendable",
    "ConfirmationRequiredError",
    "DeviceBusyError",
]
