"""Tests for the hook handler entry point."""

import json
from io import StringIO
from pathlib import Path

from cursor_agent_beacon.handler import run_hook_handler
from cursor_agent_beacon.sinks.file import FileStatusSink


def test_run_hook_handler_writes_status_file(tmp_path: Path):
    status_file = tmp_path / "status.json"
    sink = FileStatusSink(status_file)
    payload = {
        "hook_event_name": "afterAgentResponse",
        "conversation_id": "conv-1",
        "text": "All done.",
    }

    exit_code = run_hook_handler(
        stdin=StringIO(json.dumps(payload)),
        stdout=StringIO(),
        stderr=StringIO(),
        sink=sink,
    )

    assert exit_code == 0
    saved = json.loads(status_file.read_text(encoding="utf-8"))
    assert saved["state"] == "thinking"
    assert saved["message"] == "All done."
    assert (tmp_path / "registry.json").exists()
    assert (tmp_path / "sessions" / "conv-1.json").exists()


def test_run_hook_handler_fails_open_on_invalid_json():
    stdout = StringIO()
    exit_code = run_hook_handler(
        stdin=StringIO("{not-json"),
        stdout=stdout,
        stderr=StringIO(),
        sink=FileStatusSink(Path("/tmp/unused.json")),
    )

    assert exit_code == 0
    assert json.loads(stdout.getvalue()) == {"continue": True}
