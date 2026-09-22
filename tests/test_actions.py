"""Hermetic checks for the PyIncucyte agentify boundary."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from pyincucyte import IncucyteClient, actions, context


def test_discover_has_no_missing_registered_methods():
    assert actions.discover()["missing"] == []


def test_download_dispatch_coerces_options_and_returns_strict_json(tmp_path, monkeypatch):
    seen = {}

    def fake_fetch(self, options=None, **kwargs):
        seen.update(options=options, kwargs=kwargs)
        return {"options": options.to_dict(), "kwargs": kwargs}

    monkeypatch.setattr(IncucyteClient, "fetch", fake_fetch)
    result = actions.dispatch(
        "download",
        {
            "host": "example.invalid",
            "options": {"output": str(tmp_path / "out"), "vessels": ["38"],
                        "channels": "phase"},
        },
        root=str(tmp_path / "credentials"),
    )
    assert result["ok"] is True, result
    assert seen["options"].vessels == [38]
    json.dumps(result, allow_nan=False)


def test_probe_dispatch_is_read_only_and_uses_explicit_host(tmp_path, monkeypatch):
    monkeypatch.setattr(IncucyteClient, "probe", lambda self: {"host": self.host})
    result = actions.dispatch(
        "probe_device",
        {"host": "example.invalid"},
        root=str(tmp_path / "credentials"),
    )
    assert result["ok"] is True, result
    assert result["result"]["host"] == "example.invalid"
    assert result["mutates"] is False


def test_equivalent_script_is_root_aware_and_compiles(tmp_path):
    script = actions.build_equivalent_script(
        "download",
        {"host": "example.invalid", "options": {"output": "out", "odd-key": None}},
        str(tmp_path),
    )
    compile(script, "<equivalent-script>", "exec")
    assert repr(str(tmp_path)) in script


def test_context_read_search_unknown_and_artifact():
    assert "PyIncucyte" in context.read()
    assert context.search("preview")["results"]
    unknown = context.read("not-a-topic", format="json")
    assert unknown["ok"] is False
    assert json.dumps(context.export_context(), allow_nan=False)


def test_both_runner_entrypoints_return_json(tmp_path):
    runners = [
        Path(__file__).parents[1] / ".claude/skills/pyincucyte/scripts/pyincucyte_runner.py",
        Path(__file__).parents[1] / ".codex/skills/pyincucyte/scripts/pyincucyte_runner.py",
    ]
    for runner in runners:
        completed = subprocess.run(
            [sys.executable, str(runner), "discover"],
            capture_output=True, text=True, check=False,
        )
        payload = json.loads(completed.stdout)
        assert payload["ok"] is True, completed.stderr
        assert payload["registered"]


def test_bad_runner_json_is_a_clean_error():
    runner = Path(__file__).parents[1] / ".claude/skills/pyincucyte/scripts/pyincucyte_runner.py"
    completed = subprocess.run(
        [sys.executable, str(runner), "run", "not-json"],
        capture_output=True, text=True, check=False,
    )
    payload = json.loads(completed.stdout)
    assert payload["ok"] is False
