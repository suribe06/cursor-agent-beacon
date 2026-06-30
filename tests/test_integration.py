"""End-to-end hook → registry → HTTP payload path."""

from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from cursor_agent_beacon.config import BeaconConfig
from cursor_agent_beacon.handler import run_hook_handler
from cursor_agent_beacon.sinks import build_sinks


def test_hook_pipeline_writes_focused_status_for_http(tmp_path: Path):
    status_file = tmp_path / "status.json"
    config = BeaconConfig(
        enable_log_sink=False,
        enable_file_sink=True,
        status_file=status_file,
        http_url="http://127.0.0.1:1/status",
        http_timeout_seconds=0.01,
    )
    payload = {
        "hook_event_name": "beforeShellExecution",
        "conversation_id": "conv-a",
        "command": "pytest -q",
    }

    with patch("urllib.request.urlopen") as urlopen:
        urlopen.side_effect = OSError("down")
        exit_code = run_hook_handler(
            stdin=StringIO(json.dumps(payload)),
            stdout=StringIO(),
            stderr=StringIO(),
            sink=build_sinks(config),
        )

    assert exit_code == 0
    status = json.loads(status_file.read_text(encoding="utf-8"))
    assert status["state"] == "running_shell"
    assert status["focused_conversation_id"] == "conv-a"
    assert (tmp_path / "registry.json").is_file()
