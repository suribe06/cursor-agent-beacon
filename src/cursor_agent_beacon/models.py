"""Shared data models for hook events and agent status."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

try:
    from enum import StrEnum
except ImportError:  # Python < 3.11

    class StrEnum(str, Enum):
        """Backport of enum.StrEnum for Python 3.10."""


class AgentState(StrEnum):
    """High-level agent states surfaced to consumers."""

    IDLE = "idle"
    WAITING = "waiting"
    THINKING = "thinking"
    RUNNING_SHELL = "running_shell"
    RUNNING_MCP = "running_mcp"
    SUCCESS = "success"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class AgentStatus:
    """Normalized status emitted by the hook handler."""

    state: AgentState
    message: str
    hook_event_name: str
    conversation_id: str | None = None
    generation_id: str | None = None
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["state"] = self.state.value
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> AgentStatus:
        default_ts = datetime.now(timezone.utc).isoformat()
        return cls(
            state=AgentState(str(payload["state"])),
            message=str(payload.get("message", "")),
            hook_event_name=str(payload.get("hook_event_name", "bridge")),
            conversation_id=payload.get("conversation_id"),
            generation_id=payload.get("generation_id"),
            timestamp=str(payload.get("timestamp", default_ts)),
            metadata=dict(payload.get("metadata") or {}),
        )

    def serial_line(self) -> str:
        """Format used by the future Arduino bridge: STATUS|state|message."""
        safe_message = self.message.replace("|", "/")[:64]
        return f"STATUS|{self.state.value}|{safe_message}"


@dataclass(frozen=True, slots=True)
class HookEvent:
    """Parsed Cursor hook stdin payload."""

    hook_event_name: str
    raw: dict[str, Any]
    conversation_id: str | None = None
    generation_id: str | None = None
    model: str | None = None
    cursor_version: str | None = None
    workspace_roots: tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> HookEvent:
        roots = payload.get("workspace_roots") or []
        return cls(
            hook_event_name=str(payload.get("hook_event_name", "unknown")),
            raw=payload,
            conversation_id=payload.get("conversation_id"),
            generation_id=payload.get("generation_id"),
            model=payload.get("model"),
            cursor_version=payload.get("cursor_version"),
            workspace_roots=tuple(str(root) for root in roots),
        )
