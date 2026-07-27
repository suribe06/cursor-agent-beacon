"""HTTP status sink for the local bridge service."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

from cursor_agent_beacon.models import AgentStatus
from cursor_agent_beacon.session_registry import SessionRegistry


class HttpStatusSink:
    """POST display-focused status to the local bridge endpoint."""

    def __init__(
        self,
        url: str,
        timeout_seconds: float = 1.0,
        *,
        registry: SessionRegistry | None = None,
        focused_status_file: Path | None = None,
    ) -> None:
        self._url = url
        self._timeout_seconds = timeout_seconds
        self._registry = registry
        self._focused_status_file = focused_status_file

    def publish(self, status: AgentStatus) -> None:
        payload = self._bridge_payload(self._display_payload(status))
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

    @staticmethod
    def _bridge_payload(raw: dict) -> dict:
        """Keep POSTs small — bridge rejects bodies over 64 KiB."""
        meta = raw.get("metadata")
        if not isinstance(meta, dict):
            meta = {}
        slim_meta = {
            key: meta[key]
            for key in (
                "duration_ms",
                "failed",
                "stop_status",
                "loop_count",
                "tool_name",
                "last_tool",
                "subagent_type",
                "response_length",
            )
            if key in meta
        }
        command = meta.get("command")
        if isinstance(command, str) and command.strip():
            slim_meta["command"] = command.strip()[:120]
        return {
            "state": raw.get("state"),
            "message": raw.get("message"),
            "hook_event_name": raw.get("hook_event_name"),
            "conversation_id": raw.get("conversation_id") or raw.get("id"),
            "generation_id": raw.get("generation_id"),
            "project": raw.get("project"),
            "workspace_root": raw.get("workspace_root"),
            "label": raw.get("label"),
            "timestamp": raw.get("timestamp") or raw.get("updated_at"),
            "metadata": slim_meta,
        }

    def _display_payload(self, status: AgentStatus) -> dict:
        """Use focused status.json when available (multi-session auto focus)."""
        if self._focused_status_file and self._focused_status_file.is_file():
            try:
                return json.loads(self._focused_status_file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                print(
                    f"[cursor-agent-beacon] http sink read failed: {exc}",
                    file=sys.stderr,
                    flush=True,
                )

        if self._registry is not None:
            try:
                self._registry.publish(status)
                raw = self._registry.status_path.read_text(encoding="utf-8")
                return json.loads(raw)
            except (OSError, json.JSONDecodeError) as exc:
                print(
                    f"[cursor-agent-beacon] http sink registry failed: {exc}",
                    file=sys.stderr,
                    flush=True,
                )

        return status.to_dict()
