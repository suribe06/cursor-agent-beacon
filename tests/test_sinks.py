"""Tests for sink composition."""

from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from cursor_agent_beacon.config import BeaconConfig
from cursor_agent_beacon.models import AgentState, AgentStatus
from cursor_agent_beacon.sinks import MultiStatusSink, build_sinks


def _status() -> AgentStatus:
    return AgentStatus(
        state=AgentState.THINKING,
        message="Planning",
        hook_event_name="afterAgentThought",
        conversation_id="conv-1",
    )


def test_build_sinks_with_http_only_uses_registry(tmp_path: Path):
    status_file = tmp_path / "status.json"
    config = BeaconConfig(
        enable_log_sink=False,
        enable_file_sink=False,
        status_file=status_file,
        http_url="http://127.0.0.1:1/status",
        http_timeout_seconds=0.01,
    )

    sink = build_sinks(config)
    assert isinstance(sink, MultiStatusSink)

    with patch("urllib.request.urlopen") as urlopen:
        urlopen.side_effect = OSError("connection refused")
        sink.publish(_status())

    assert status_file.is_file()
    payload = json.loads(status_file.read_text(encoding="utf-8"))
    assert payload["state"] == "thinking"


def test_multi_sink_logs_failures():
    class _BrokenSink:
        def publish(self, status: AgentStatus) -> None:
            raise RuntimeError("boom")

    stderr = StringIO()
    sink = MultiStatusSink([_BrokenSink()])

    with patch("sys.stderr", stderr):
        sink.publish(_status())

    assert "sink _BrokenSink failed" in stderr.getvalue()
