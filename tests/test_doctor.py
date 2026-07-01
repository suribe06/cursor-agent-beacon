"""Tests for doctor and status display."""

from __future__ import annotations

import json
from pathlib import Path

from cursor_agent_beacon.doctor import (
    CheckResult,
    _parse_wrapper_bin,
    doctor_exit_code,
    format_doctor_report,
    format_status_report,
    read_status_payload,
    run_doctor,
)
from cursor_agent_beacon.install import merge_hooks_config


def test_parse_wrapper_bin():
    text = '#!/bin/bash\nexec "/repo/.venv/bin/cursor-agent-beacon" run\n'
    assert _parse_wrapper_bin(text) == Path("/repo/.venv/bin/cursor-agent-beacon")


def test_run_doctor_all_ok(tmp_path: Path, monkeypatch):
    cursor_dir = tmp_path / ".cursor"
    status_dir = tmp_path / "share/cursor-agent-beacon"
    status_file = status_dir / "status.json"
    beacon = tmp_path / "cursor-agent-beacon"
    beacon.write_text("#!/bin/sh\n", encoding="utf-8")
    beacon.chmod(0o755)
    wrapper = cursor_dir / "hooks" / "cursor-agent-beacon.sh"
    wrapper.parent.mkdir(parents=True)
    wrapper.write_text(
        f'#!/bin/bash\nexec "{beacon}" run\n',
        encoding="utf-8",
    )
    wrapper.chmod(0o755)

    hooks_path = cursor_dir / "hooks.json"
    merged = merge_hooks_config(None, "./hooks/cursor-agent-beacon.sh")
    hooks_path.write_text(json.dumps(merged), encoding="utf-8")

    monkeypatch.setattr(
        "cursor_agent_beacon.doctor.resolve_beacon_bin",
        lambda _explicit=None: beacon.resolve(),
    )
    monkeypatch.setattr(
        "cursor_agent_beacon.doctor.gnome_extension_available",
        lambda: False,
    )

    results = run_doctor(
        cursor_dir=cursor_dir,
        status_file=status_file,
        wrapper_path=wrapper,
    )
    assert doctor_exit_code(results) == 0
    failed = {
        item.name for item in results if not item.ok and item.name != "cursor restart"
    }
    assert not failed


def test_run_doctor_missing_wrapper(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(
        "cursor_agent_beacon.doctor.resolve_beacon_bin",
        lambda _explicit=None: tmp_path / "beacon",
    )
    monkeypatch.setattr(
        "cursor_agent_beacon.doctor.gnome_extension_available",
        lambda: False,
    )
    (tmp_path / "beacon").write_text("", encoding="utf-8")

    results = run_doctor(
        cursor_dir=tmp_path / ".cursor",
        status_file=tmp_path / "status.json",
        wrapper_path=tmp_path / "missing.sh",
    )
    assert doctor_exit_code(results) == 1
    assert any(item.name == "hook wrapper" and not item.ok for item in results)


def test_doctor_probe_writes_status(tmp_path: Path, monkeypatch):
    cursor_dir = tmp_path / ".cursor"
    status_file = tmp_path / "share/status.json"
    beacon = tmp_path / "cursor-agent-beacon"
    beacon.write_text("#!/bin/sh\n", encoding="utf-8")
    beacon.chmod(0o755)
    wrapper = cursor_dir / "hooks/cursor-agent-beacon.sh"
    wrapper.parent.mkdir(parents=True)
    wrapper.write_text(f'exec "{beacon}" run\n', encoding="utf-8")
    wrapper.chmod(0o755)
    hooks_path = cursor_dir / "hooks.json"
    hooks_path.write_text(
        json.dumps(merge_hooks_config(None, "./hooks/cursor-agent-beacon.sh")),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "cursor_agent_beacon.doctor.resolve_beacon_bin",
        lambda _explicit=None: beacon.resolve(),
    )
    monkeypatch.setattr(
        "cursor_agent_beacon.doctor.gnome_extension_available",
        lambda: False,
    )

    results = run_doctor(
        cursor_dir=cursor_dir,
        status_file=status_file,
        wrapper_path=wrapper,
        probe=True,
    )
    probe = next(item for item in results if item.name == "hook probe")
    assert probe.ok
    assert status_file.is_file()


def test_format_status_report():
    text = format_status_report(
        {
            "state": "thinking",
            "message": "Planning",
            "project": "beacon",
            "hook_event_name": "afterAgentThought",
            "timestamp": "2026-01-01T00:00:00+00:00",
            "active_count": 2,
        },
        status_file=Path("/tmp/status.json"),
    )
    assert "thinking" in text
    assert "Planning" in text
    assert "Active:   2" in text


def test_read_status_payload(tmp_path: Path):
    path = tmp_path / "status.json"
    path.write_text('{"state":"idle"}', encoding="utf-8")
    assert read_status_payload(path)["state"] == "idle"


def test_format_doctor_report_marks_failures():
    report = format_doctor_report(
        [
            CheckResult("hooks.json", False, "missing", hint="Run setup"),
            CheckResult("cursor restart", True, "reminder"),
        ]
    )
    assert "✗" in report
    assert "failed" in report
