"""Shared data models for hook events and agent status."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from cursor_agent_beacon.compat import StrEnum
from cursor_agent_beacon.protocol import StatusCommand


class AgentState(StrEnum):
    """High-level agent states surfaced to consumers."""

    IDLE = "idle"
    WAITING = "waiting"
    THINKING = "thinking"
    RUNNING_SHELL = "running_shell"
    RUNNING_MCP = "running_mcp"
    SUCCESS = "success"
    ERROR = "error"


def parse_model_params(raw: Any) -> dict[str, str]:
    """Normalize Cursor `model_params` list into an id→value map."""
    if not isinstance(raw, list):
        return {}
    out: dict[str, str] = {}
    for item in raw:
        if not isinstance(item, dict):
            continue
        key = item.get("id")
        if key is None:
            continue
        out[str(key)] = str(item.get("value", ""))
    return out


def _coerce_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _coerce_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True, slots=True)
class AgentStatus:
    """Normalized status emitted by the hook handler."""

    state: AgentState
    message: str
    hook_event_name: str
    conversation_id: str | None = None
    generation_id: str | None = None
    project: str | None = None
    workspace_root: str | None = None
    label: str | None = None
    model: str | None = None
    model_id: str | None = None
    effort: str | None = None
    context_usage_percent: float | None = None
    context_tokens: int | None = None
    context_window_size: int | None = None
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def model_label(self) -> str | None:
        """Raw model id/slug from Cursor — no pretty aliases.

        Skip the placeholder name ``default`` (Cursor often sends that as
        ``model`` while the real slug lives in ``model_id``).
        """
        for value in (self.model_id, self.model):
            if not isinstance(value, str):
                continue
            cleaned = value.strip()
            if cleaned and cleaned.lower() != "default":
                return cleaned
        return None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["state"] = self.state.value
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> AgentStatus:
        default_ts = datetime.now(timezone.utc).isoformat()
        model = payload.get("model")
        model_id = payload.get("model_id")
        meta = dict(payload.get("metadata") or {})
        pct = _coerce_float(
            payload.get("context_usage_percent", meta.get("context_usage_percent"))
        )
        tokens = _coerce_int(
            payload.get("context_tokens", meta.get("context_tokens"))
        )
        window = _coerce_int(
            payload.get("context_window_size", meta.get("context_window_size"))
        )
        return cls(
            state=AgentState(str(payload["state"])),
            message=str(payload.get("message", "")),
            hook_event_name=str(payload.get("hook_event_name", "bridge")),
            conversation_id=payload.get("conversation_id"),
            generation_id=payload.get("generation_id"),
            project=payload.get("project"),
            workspace_root=payload.get("workspace_root"),
            label=payload.get("label"),
            model=model if isinstance(model, str) else None,
            model_id=model_id if isinstance(model_id, str) else None,
            effort=payload.get("effort")
            if isinstance(payload.get("effort"), str)
            else None,
            context_usage_percent=pct,
            context_tokens=tokens,
            context_window_size=window,
            timestamp=str(payload.get("timestamp", default_ts)),
            metadata=meta,
        )

    def model_caption(self) -> str:
        """ASCII model/effort line for the VIEWE display (separate from message)."""
        bits = [bit for bit in (self.model_label, self.effort) if bit]
        return " ".join(bits)

    def serial_line(self) -> str:
        """Format used by the VIEWE bridge: STATUS|state|message|model|ctx."""
        message = self.message
        # State label already shows Ready/Thinking — avoid duplicating it.
        if message in {"Ready", "Thinking...", "Session started"}:
            message = ""
        ctx = None
        if self.context_usage_percent is not None:
            ctx = max(0, min(100, int(round(self.context_usage_percent))))
        return StatusCommand(
            state=self.state.value,
            message=message,
            model=self.model_caption(),
            context_pct=ctx,
        ).serial_line()


@dataclass(frozen=True, slots=True)
class HookEvent:
    """Parsed Cursor hook stdin payload."""

    hook_event_name: str
    raw: dict[str, Any]
    conversation_id: str | None = None
    generation_id: str | None = None
    model: str | None = None
    model_id: str | None = None
    model_params: tuple[dict[str, str], ...] = field(default_factory=tuple)
    cursor_version: str | None = None
    workspace_roots: tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> HookEvent:
        roots = payload.get("workspace_roots") or []
        raw_params = payload.get("model_params") or []
        params: list[dict[str, str]] = []
        if isinstance(raw_params, list):
            for item in raw_params:
                if not isinstance(item, dict) or item.get("id") is None:
                    continue
                params.append(
                    {"id": str(item["id"]), "value": str(item.get("value", ""))}
                )
        model_id = payload.get("model_id")
        return cls(
            hook_event_name=str(payload.get("hook_event_name", "unknown")),
            raw=payload,
            conversation_id=payload.get("conversation_id"),
            generation_id=payload.get("generation_id"),
            model=payload.get("model"),
            model_id=str(model_id) if model_id is not None else None,
            model_params=tuple(params),
            cursor_version=payload.get("cursor_version"),
            workspace_roots=tuple(str(root) for root in roots),
        )
