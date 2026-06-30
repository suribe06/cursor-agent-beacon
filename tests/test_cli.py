"""Tests for CLI commands."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_cli_help():
    result = subprocess.run(
        [sys.executable, "-m", "cursor_agent_beacon.cli", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "install-hooks" in result.stdout


def test_cli_map_sample_event():
    event = Path("examples/sample-events/stop_completed.json")
    result = subprocess.run(
        [sys.executable, "-m", "cursor_agent_beacon.cli", "map", str(event)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert '"state": "success"' in result.stdout
