#!/usr/bin/env python
"""Headless JSON runner for the PyIncucyte agent control boundary."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _bootstrap() -> None:
    here = Path(__file__).resolve()
    for ancestor in here.parents:
        for candidate in (ancestor / "src", ancestor):
            if (candidate / "pyincucyte" / "actions.py").is_file():
                if str(candidate) not in sys.path:
                    sys.path.insert(0, str(candidate))
                return


def _load_request(value: str | None) -> dict:
    if not value:
        return {}
    path = Path(value)
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8-sig"))
    return json.loads(value)


def _emit(value: object) -> int:
    print(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False))
    return 0 if not isinstance(value, dict) or value.get("ok", True) else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="PyIncucyte headless agent runner")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("run", "submit", "script"):
        sub.add_parser(name).add_argument("request")
    sub.add_parser("inspect").add_argument("request", nargs="?")
    sub.add_parser("describe").add_argument("action", nargs="?")
    sub.add_parser("discover")
    context = sub.add_parser("context")
    context.add_argument("topic", nargs="?")
    context.add_argument("--search", dest="query")
    args = parser.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    except Exception:
        pass
    _bootstrap()
    try:
        if args.command == "context":
            if args.topic is not None and args.query is not None:
                raise ValueError("context accepts a topic or --search, not both")
            from pyincucyte import context as guide
            result = (guide.search(args.query) if args.query is not None else
                      guide.read(args.topic or "overview", format="json"))
            return _emit(result)
        from pyincucyte import actions
        request = _load_request(getattr(args, "request", None))
        if not isinstance(request, dict):
            raise ValueError("request must be a JSON object")
        if args.command in ("run", "submit"):
            return _emit(actions.dispatch(request.get("action"),
                                          request.get("params"),
                                          request.get("root")))
        if args.command == "script":
            print(actions.build_equivalent_script(
                request.get("action"), request.get("params") or {},
                request.get("root")))
            return 0
        if args.command == "inspect":
            return _emit(actions.dispatch("inspect", request.get("params") or {},
                                           request.get("root")))
        if args.command == "describe":
            return _emit(actions.describe(args.action))
        if args.command == "discover":
            result = actions.discover()
            result["context"] = {
                "read": "context [topic]",
                "search": "context --search <query>",
            }
            return _emit(result)
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        return _emit({"ok": False, "error": f"bad request: {exc}"})
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
