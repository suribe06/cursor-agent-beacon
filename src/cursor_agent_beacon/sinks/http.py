"""HTTP status sink for the local bridge service."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

from cursor_agent_beacon.models import AgentStatus


class HttpStatusSink:
    """POST display-focused status to the local bridge endpoint."""

    def __init__(
        self,
        url: str,
        timeout_seconds: float = 1.0,
        focused_status_file: Path | None = None,
    ) -> None:
        self._url = url
        self._timeout_seconds = timeout_seconds
        self._focused_status_file = focused_status_file

    def publish(self, status: AgentStatus) -> None:
        payload = self._display_payload(status)
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self._url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout_seconds):
                return
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            print(
                f"[cursor-agent-beacon] http sink failed: {exc}",
                file=sys.stderr,
                flush=True,
            )

    def _display_payload(self, status: AgentStatus) -> dict:
        """Use focused status.json when available (multi-session auto focus)."""
        if self._focused_status_file and self._focused_status_file.is_file():
            try:
                return json.loads(self._focused_status_file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                pass
        return status.to_dict()
