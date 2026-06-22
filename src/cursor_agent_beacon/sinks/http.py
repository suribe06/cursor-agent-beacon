"""HTTP status sink for the local bridge service."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

from cursor_agent_beacon.models import AgentStatus


class HttpStatusSink:
    """POST normalized status to a local bridge endpoint."""

    def __init__(self, url: str, timeout_seconds: float = 1.0) -> None:
        self._url = url
        self._timeout_seconds = timeout_seconds

    def publish(self, status: AgentStatus) -> None:
        payload = {
            "state": status.state.value,
            "message": status.message,
            "hook_event_name": status.hook_event_name,
            "conversation_id": status.conversation_id,
            "timestamp": status.timestamp,
        }
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
