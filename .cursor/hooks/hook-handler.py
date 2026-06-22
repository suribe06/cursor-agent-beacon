#!/usr/bin/env python3
"""Cursor hook entry point — thin wrapper around cursor_agent_beacon."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cursor_agent_beacon.handler import run_hook_handler  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(run_hook_handler())
