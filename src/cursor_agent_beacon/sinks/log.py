"""Structured logging sink (stderr)."""

from __future__ import annotations

import json
import sys
from typing import TextIO

from cursor_agent_beacon.models import AgentStatus


class LogStatusSink:
    """Write JSON lines to stderr for observability."""

    def __init__(self, stream: TextIO | None = None) -> None:
        self._stream = stream or sys.stderr

    def publish(self, status: AgentStatus) -> None:
        try:
            line = json.dumps(status.to_dict(), separators=(",", ":"))
            print(line, file=self._stream, flush=True)
        except Exception as exc:  # noqa: BLE001 - sink must never crash hooks
            print(
                f"[cursor-agent-beacon] log sink failed: {exc}",
                file=self._stream,
                flush=True,
            )
