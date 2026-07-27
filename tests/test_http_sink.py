"""Tests for HTTP sink display focus."""

import json
from pathlib import Path

from cursor_agent_beacon.models import AgentState, AgentStatus
from cursor_agent_beacon.sinks.http import HttpStatusSink


def test_http_sink_uses_focused_status_file(tmp_path: Path):
    status_file = tmp_path / "status.json"
    status_file.write_text(
        json.dumps(
            {
                "state": "thinking",
                "message": "Focused session",
                "conversation_id": "conv-b",
                "focus_mode": "auto",
            }
        ),
        encoding="utf-8",
    )
    sink = HttpStatusSink(
        "http://127.0.0.1:9/unused",
        focused_status_file=status_file,
    )
    payload = sink._display_payload(
        AgentStatus(
            state=AgentState.SUCCESS,
            message="Background session",
            hook_event_name="afterAgentResponse",
            conversation_id="conv-a",
        )
    )
    assert payload["state"] == "thinking"
    assert payload["message"] == "Focused session"
    assert payload["conversation_id"] == "conv-b"


def test_bridge_payload_strips_bulky_metadata():
    slim = HttpStatusSink._bridge_payload(
        {
            "state": "running_shell",
            "message": "npm test",
            "hook_event_name": "beforeShellExecution",
            "id": "conv-1",
            "metadata": {
                "command": "x" * 5000,
                "cwd": "/tmp",
                "failed": False,
            },
        }
    )
    assert slim["conversation_id"] == "conv-1"
    assert len(slim["metadata"]["command"]) <= 120
    assert "cwd" not in slim["metadata"]
