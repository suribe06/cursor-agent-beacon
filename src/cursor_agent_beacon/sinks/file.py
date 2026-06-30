"""Persist multi-session status snapshots to disk."""

from __future__ import annotations

import sys
from pathlib import Path

from cursor_agent_beacon.models import AgentStatus
from cursor_agent_beacon.session_registry import SessionRegistry


class FileStatusSink:
    """Write per-session files, registry index, and focused status.json."""

    def __init__(self, registry: SessionRegistry | Path) -> None:
        if isinstance(registry, Path):
            self._registry = SessionRegistry(registry.parent)
        else:
            self._registry = registry

    def publish(self, status: AgentStatus) -> None:
        try:
            self._registry.publish(status)
        except Exception as exc:  # noqa: BLE001 - sink must never crash hooks
            print(
                f"[cursor-agent-beacon] file sink failed: {exc}",
                file=sys.stderr,
                flush=True,
            )
