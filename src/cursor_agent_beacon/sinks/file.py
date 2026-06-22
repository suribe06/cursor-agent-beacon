"""Persist the latest status to a JSON file."""

from __future__ import annotations

import json
from pathlib import Path

from cursor_agent_beacon.models import AgentStatus


class FileStatusSink:
    """Write the latest status snapshot to disk."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def publish(self, status: AgentStatus) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = self._path.with_suffix(".tmp")
            temp_path.write_text(
                json.dumps(status.to_dict(), indent=2) + "\n",
                encoding="utf-8",
            )
            temp_path.replace(self._path)
        except Exception:
            # Fail silently — hooks must never block Cursor.
            return
