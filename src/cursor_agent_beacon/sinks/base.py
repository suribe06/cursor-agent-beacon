"""Status sink protocol."""

from __future__ import annotations

from typing import Protocol

from cursor_agent_beacon.models import AgentStatus


class StatusSink(Protocol):
    """Consumer for normalized agent status updates."""

    def publish(self, status: AgentStatus) -> None:
        """Emit a status update. Must not raise to callers."""
