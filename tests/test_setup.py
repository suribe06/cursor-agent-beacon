"""Tests for one-shot setup."""

from __future__ import annotations

from pathlib import Path

from cursor_agent_beacon.install import write_user_hooks
from cursor_agent_beacon.setup import SetupResult, format_next_steps, run_setup


def test_write_user_hooks_pins_beacon_bin(tmp_path: Path, monkeypatch):
    cursor_dir = tmp_path / ".cursor"
    status_file = tmp_path / "share/status.json"
    beacon = tmp_path / "bin" / "cursor-agent-beacon"
    beacon.parent.mkdir(parents=True)
    beacon.write_text("#!/bin/sh\n", encoding="utf-8")

    monkeypatch.setattr(
        "cursor_agent_beacon.install.DEFAULT_STATUS_FILE",
        status_file,
    )
    write_user_hooks(
        cursor_dir=cursor_dir,
        status_file=status_file,
        beacon_bin=beacon,
    )

    wrapper = cursor_dir / "hooks" / "cursor-agent-beacon.sh"
    text = wrapper.read_text(encoding="utf-8")
    assert str(beacon.resolve()) in text
    assert " run" in text


def test_run_setup_hooks_only(tmp_path: Path, monkeypatch):
    cursor_dir = tmp_path / ".cursor"
    status_file = tmp_path / "share/status.json"
    beacon = tmp_path / "cursor-agent-beacon"
    beacon.write_text("#!/bin/sh\n", encoding="utf-8")
    beacon.chmod(0o755)

    def _write(**kwargs):
        return write_user_hooks(
            cursor_dir=cursor_dir,
            status_file=status_file,
            **kwargs,
        )

    monkeypatch.setattr("cursor_agent_beacon.setup.write_user_hooks", _write)
    monkeypatch.setattr(
        "cursor_agent_beacon.setup.gnome_extension_available",
        lambda: False,
    )

    result = run_setup(hooks_only=True, beacon_bin=beacon)
    assert result.beacon_bin == beacon.resolve()
    assert result.gnome_path is None
    assert (cursor_dir / "hooks" / "cursor-agent-beacon.sh").is_file()


def test_format_next_steps_includes_restart_cursor():
    result = SetupResult(
        hooks_path=Path("/home/u/.cursor/hooks.json"),
        status_file=Path("/home/u/.local/share/cursor-agent-beacon/status.json"),
        beacon_bin=Path("/repo/.venv/bin/cursor-agent-beacon"),
    )
    text = format_next_steps(result)
    assert "Restart Cursor" in text
    assert "Hooks:" in text
