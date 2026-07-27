#!/usr/bin/env python3
"""Cursor hook entry point — thin wrapper around cursor_agent_beacon."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# Bake bridge URL for this repo so project hooks update the VIEWE panel too.
# User hooks (~/.cursor) already set this; project hooks previously only wrote
# .cursor-agent-beacon/ and left the panel stuck on the last thinking POST.
_hardware_env = ROOT / "config" / "hardware.env"
if _hardware_env.is_file():
    for _line in _hardware_env.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if not _line or _line.startswith("#") or "=" not in _line:
            continue
        _key, _, _val = _line.partition("=")
        _key = _key.strip()
        if _key and _key not in os.environ:
            os.environ[_key] = _val.strip().strip('"').strip("'")

os.environ.setdefault(
    "CURSOR_AGENT_BEACON_HTTP_URL",
    "http://127.0.0.1:8765/status",
)
os.environ.setdefault(
    "CURSOR_AGENT_BEACON_STATUS_FILE",
    str(Path.home() / ".local/share/cursor-agent-beacon/status.json"),
)

from cursor_agent_beacon.handler import run_hook_handler  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(run_hook_handler())
