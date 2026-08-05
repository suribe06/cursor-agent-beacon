"""Tests for display.toml preferences."""

from __future__ import annotations

import json
from pathlib import Path

from cursor_agent_beacon.display_prefs import (
    DisplayPrefs,
    clear_display_prefs_cache,
    ensure_display_config,
    load_display_prefs,
    parse_display_toml,
)
from cursor_agent_beacon.models import AgentState, AgentStatus


def test_parse_display_toml_defaults_and_overrides():
    text = """
    [show]
    model = false
    effort = true
    context = false
    # comment
    message = false
    attachments = false
    sandbox = true

    [extension]
    panel_badge = false
    """
    prefs = parse_display_toml(text)
    assert prefs == DisplayPrefs(
        model=False,
        effort=True,
        context=False,
        message=False,
        attachments=False,
        sandbox=True,
        panel_badge=False,
    )


def test_ensure_display_config_creates_once(tmp_path: Path):
    path = tmp_path / "display.toml"
    created = ensure_display_config(path)
    assert created == path
    assert path.is_file()
    original = path.read_text(encoding="utf-8")
    path.write_text(
        original.replace("context = true", "context = false"), encoding="utf-8"
    )
    ensure_display_config(path)
    assert "context = false" in path.read_text(encoding="utf-8")


def test_load_display_prefs_respects_env(tmp_path: Path, monkeypatch):
    clear_display_prefs_cache()
    path = tmp_path / "display.toml"
    path.write_text(
        "[show]\nmodel = false\neffort = false\ncontext = true\n"
        "message = true\nattachments = true\nsandbox = true\n"
        "[extension]\npanel_badge = true\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CURSOR_AGENT_BEACON_DISPLAY_CONFIG", str(path))
    prefs = load_display_prefs(use_cache=False)
    assert prefs.model is False
    assert prefs.effort is False
    assert prefs.context is True
    clear_display_prefs_cache()


def test_serial_line_filters_by_prefs(tmp_path: Path, monkeypatch):
    clear_display_prefs_cache()
    path = tmp_path / "display.toml"
    path.write_text(
        "[show]\nmodel = true\neffort = false\ncontext = false\n"
        "message = false\nattachments = true\nsandbox = true\n"
        "[extension]\npanel_badge = true\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CURSOR_AGENT_BEACON_DISPLAY_CONFIG", str(path))
    status = AgentStatus(
        state=AgentState.RUNNING_SHELL,
        message="ls -la",
        hook_event_name="beforeShellExecution",
        model_id="grok-4.5",
        effort="high",
        context_usage_percent=47.0,
    )
    line = status.serial_line()
    assert line == "STATUS|running_shell||grok-4.5"
    assert "|47" not in line
    clear_display_prefs_cache()


def test_reload_display_updates_status(tmp_path: Path, monkeypatch):
    clear_display_prefs_cache()
    config = tmp_path / "display.toml"
    config.write_text(
        "[show]\nmodel = false\neffort = true\ncontext = false\n"
        "message = true\nattachments = true\nsandbox = true\n"
        "[extension]\npanel_badge = false\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CURSOR_AGENT_BEACON_DISPLAY_CONFIG", str(config))

    status_path = tmp_path / "status.json"
    status_path.write_text(
        json.dumps(
            {
                "state": "success",
                "message": "Ready",
                "hook_event_name": "stop",
                "model_id": "grok-4.5",
                "effort": "high",
                "context_usage_percent": 40,
            }
        ),
        encoding="utf-8",
    )

    from cursor_agent_beacon.display_prefs import reload_display

    result = reload_display(status_file=status_path, push_bridge=False)
    assert result["prefs"]["show"]["model"] is False
    assert result["prefs"]["extension"]["panel_badge"] is False
    assert result["serial"] == "STATUS|success||high"
    refreshed = json.loads(status_path.read_text(encoding="utf-8"))
    assert refreshed["display"]["show"]["context"] is False
    clear_display_prefs_cache()
