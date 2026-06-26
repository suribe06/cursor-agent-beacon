"""Persist multi-session status snapshots to disk."""

from __future__ import annotations

from pathlib import Path

from cursor_agent_beacon.models import AgentStatus
from cursor_agent_beacon.session_registry import SessionRegistry


class FileStatusSink:
    """Write per-session files, registry index, and focused status.json."""

    def __init__(self, status_file: Path) -> None:
        self._registry = SessionRegistry(status_file.parent)

    def publish(self, status: AgentStatus) -> None:
        try:
            self._registry.publish(status)
        except Exception:
            return
