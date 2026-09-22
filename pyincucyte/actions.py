"""Headless, JSON-dispatchable control actions for PyIncucyte.

The registry exposes read, plan, preview, download, and one-shot watch
workflows over ``IncucyteClient``. Credential entry, logout, scheduling, and
instrument-changing commands stay outside the agent boundary.
"""
from __future__ import annotations

import dataclasses
import inspect
import math
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable

from .client import IncucyteClient
from .config import ConfigStore
from .options import ExportOptions

__all__ = [
    "ACTION_REGISTRY",
    "ActionSpec",
    "available_actions",
    "build_equivalent_script",
    "describe",
    "discover",
    "dispatch",
    "serialize",
]


def _to_options(value: Any) -> Any:
    if value is None or isinstance(value, ExportOptions):
        return value
    if isinstance(value, dict):
        return ExportOptions.from_dict(value)
    raise TypeError("options must be an object or null")


def _to_int(value: Any) -> Any:
    return None if value is None else int(value)


def _to_ints(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (list, tuple, set)):
        return [int(item) for item in value]
    return int(value)


def _to_tuple(value: Any) -> Any:
    if value is None or isinstance(value, tuple):
        return value
    if isinstance(value, (list, set)):
        return tuple(value)
    raise TypeError("value must be a list, set, tuple, or null")


_NAME_COERCERS: dict[str, Callable[[Any], Any]] = {
    "options": _to_options,
    "vessel": _to_ints,
    "site": _to_int,
    "most_recent": _to_int,
    "limit": _to_int,
    "workers": _to_int,
    "names": _to_tuple,
}


@dataclasses.dataclass(frozen=True)
class ActionSpec:
    summary: str
    method: str | None = None
    fn: Callable[..., Any] | None = None
    mutates: bool = False
    destructive: bool = False
    coerce: dict[str, Callable[[Any], Any]] = dataclasses.field(default_factory=dict)
    covers: tuple[str, ...] = ()


def _inspect(backend: IncucyteClient) -> dict[str, Any]:
    return {
        "host": backend.host,
        "probe": backend.probe(),
        "device_status": backend.device_state(),
        "vessels": backend.vessels(),
    }


ACTION_REGISTRY: dict[str, ActionSpec] = {
    "inspect": ActionSpec(
        "Ground the agent in the configured device and current vessel list.",
        fn=_inspect,
        covers=("probe", "device_state", "vessels"),
    ),
    "probe_device": ActionSpec(
        "Check whether the configured Incucyte answers.",
        method="probe",
    ),
    "device_status": ActionSpec(
        "Read the instrument activity and temperature status.",
        method="device_state",
        covers=("device_status",),
    ),
    "list_vessels": ActionSpec(
        "List vessels known to the instrument.",
        method="vessels",
    ),
    "find_vessels": ActionSpec(
        "Find vessels by name, ID, owner, plate, or channel.",
        method="find_vessels",
        coerce={"vessel": _to_ints},
    ),
    "find_scans": ActionSpec(
        "Find usable scans for a vessel or search description.",
        method="find_scans",
        coerce={"vessel": _to_ints, "most_recent": _to_int,
                "limit": _to_int},
    ),
    "plan_download": ActionSpec(
        "Plan a download and report files, frames, channels, and bytes before writing.",
        method="plan",
        coerce={"options": _to_options},
    ),
    "protocol": ActionSpec(
        "Read the acquisition protocol and progress metadata without downloading pixels.",
        method="protocol",
        coerce={"names": _to_tuple},
    ),
    "preview": ActionSpec(
        "Fetch bounded GUI-free thumbnails for identifying wells and channels.",
        method="preview",
        coerce={"site": _to_int, "workers": _to_int},
    ),
    "download": ActionSpec(
        "Download selected images into ImageJ-compatible files and a manifest.",
        method="fetch",
        mutates=True,
        coerce={"options": _to_options},
        covers=("pull", "download"),
    ),
    "watch_once": ActionSpec(
        "Poll once, resume from the ledger, and download newly available scans.",
        method="watch_once",
        mutates=True,
        coerce={"options": _to_options},
    ),
}


def serialize(value: Any) -> Any:
    """Convert a result to strict JSON-compatible values."""
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): serialize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [serialize(item) for item in value]
    item = getattr(value, "item", None)
    if callable(item):
        try:
            return serialize(item())
        except Exception:
            pass
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        try:
            return serialize(to_dict())
        except Exception:
            pass
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {field.name: serialize(getattr(value, field.name))
                for field in dataclasses.fields(value)}
    if hasattr(value, "tolist"):
        try:
            return serialize(value.tolist())
        except Exception:
            pass
    return str(value)


def _split_backend_controls(params: dict[str, Any], root: str | None):
    call_params = dict(params)
    config_home = root or call_params.pop("config_home", None)
    host = call_params.pop("host", None)
    return call_params, config_home, host


def _build_backend(root: str | None, params: dict[str, Any]):
    call_params, config_home, host = _split_backend_controls(params, root)
    store = (ConfigStore(Path(config_home) / "credentials.json")
             if config_home else None)
    return IncucyteClient(host=host, store=store), call_params


def _coerce(spec: ActionSpec, params: dict[str, Any]) -> dict[str, Any]:
    output = {}
    for key, value in params.items():
        converter = spec.coerce.get(key) or _NAME_COERCERS.get(key)
        output[key] = converter(value) if converter else value
    return output


def _safe_script(action: Any, params: Any, root: str | None) -> str:
    try:
        return build_equivalent_script(action, params if isinstance(params, dict) else {}, root)
    except Exception:
        return ""


def dispatch(action: str, params: dict[str, Any] | None = None,
             root: str | None = None) -> dict[str, Any]:
    """Run one action and return a JSON-clean envelope; never raise."""
    if not isinstance(action, str):
        return {"ok": False, "action": serialize(action),
                "error": "action must be a string",
                "available": available_actions(),
                "equivalent_script": _safe_script(action, params, root)}
    if params is not None and not isinstance(params, dict):
        return {"ok": False, "action": action,
                "error": "params must be a JSON object",
                "equivalent_script": _safe_script(action, params, root)}
    raw_params = dict(params or {})
    spec = ACTION_REGISTRY.get(action)
    if spec is None:
        return {"ok": False, "action": action,
                "error": f"Unknown action {action!r}",
                "available": available_actions(),
                "equivalent_script": _safe_script(action, raw_params, root)}
    try:
        backend, call_params = _build_backend(root, raw_params)
        result = (spec.fn(backend, **_coerce(spec, call_params))
                  if spec.fn else getattr(backend, spec.method)(
                      **_coerce(spec, call_params)))
        return {
            "ok": True,
            "action": action,
            "mutates": spec.mutates,
            "destructive": spec.destructive,
            "result": serialize(result),
            "equivalent_script": build_equivalent_script(action, raw_params, root),
        }
    except Exception as exc:  # noqa: BLE001 - the runner must return JSON
        return {
            "ok": False,
            "action": action,
            "error": f"{type(exc).__name__}: {exc}",
            "equivalent_script": _safe_script(action, raw_params, root),
        }


def _render_call_args(params: dict[str, Any]) -> str:
    valid, invalid = [], []
    for key, value in params.items():
        if str(key).isidentifier():
            valid.append(f"{key}={value!r}")
        else:
            invalid.append(f"{str(key)!r}: {value!r}")
    if invalid:
        valid.append("**{" + ", ".join(invalid) + "}")
    return ", ".join(valid)


def _script_backend(root: str | None, params: dict[str, Any]):
    call_params, config_home, host = _split_backend_controls(params, root)
    if config_home:
        header = (
            "from pathlib import Path\n"
            "from pyincucyte import ConfigStore, IncucyteClient\n\n"
            f"backend = IncucyteClient(host={host!r}, "
            f"store=ConfigStore(Path({str(config_home)!r}) / 'credentials.json'))\n"
        )
    else:
        header = (
            "from pyincucyte import IncucyteClient\n\n"
            f"backend = IncucyteClient(host={host!r})\n"
        )
    return header, call_params


def build_equivalent_script(action: str, params: dict[str, Any] | None = None,
                            root: str | None = None) -> str:
    params = dict(params or {})
    spec = ACTION_REGISTRY.get(action)
    header, call_params = _script_backend(root, params)
    if spec is None:
        body = f"# unknown action {action!r}"
    elif spec.method:
        body = f"backend.{spec.method}({_render_call_args(call_params)})"
    else:
        body = (
            "from pyincucyte import actions\n"
            f"actions.dispatch({action!r}, {params!r}, {root!r})"
        )
    return header + body + "\n"


def available_actions() -> list[str]:
    return sorted(ACTION_REGISTRY)


def describe(action: str | None = None) -> dict[str, Any]:
    if action is None:
        return {"ok": True, "actions": {
            name: {"summary": spec.summary, "mutates": spec.mutates,
                   "destructive": spec.destructive}
            for name, spec in sorted(ACTION_REGISTRY.items())}}
    if not isinstance(action, str):
        return {"ok": False, "error": "action must be a string",
                "available": available_actions()}
    spec = ACTION_REGISTRY.get(action)
    if spec is None:
        return {"ok": False, "error": f"Unknown action {action!r}",
                "available": available_actions()}
    target = spec.fn or getattr(IncucyteClient, spec.method, None)
    try:
        signature = str(inspect.signature(target)) if target else "(...)"
    except (TypeError, ValueError):
        signature = "(...)"
    return {"ok": True, "action": action, "summary": spec.summary,
            "mutates": spec.mutates, "destructive": spec.destructive,
            "binds_to": spec.method or "wrapper", "signature": signature}


def discover() -> dict[str, Any]:
    methods = {}
    for name, member in inspect.getmembers(IncucyteClient, predicate=inspect.isfunction):
        if name.startswith("_"):
            continue
        try:
            signature = str(inspect.signature(member))
        except (TypeError, ValueError):
            signature = "(...)"
        methods[name] = {
            "signature": signature,
            "summary": (inspect.getdoc(member) or "").strip().split("\n")[0],
        }
    bound = {spec.method for spec in ACTION_REGISTRY.values() if spec.method}
    covered = {method for spec in ACTION_REGISTRY.values() for method in spec.covers}
    exposed = bound | covered
    return {
        "ok": True,
        "registered": available_actions(),
        "methods": methods,
        "unregistered": sorted(set(methods) - exposed),
        "missing": sorted(method for method in bound if method not in methods),
    }
