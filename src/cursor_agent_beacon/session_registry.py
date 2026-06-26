"""Multi-session registry for cursor-agent-beacon."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cursor_agent_beacon.models import AgentState, AgentStatus

_BUSY_STATES = {
    AgentState.WAITING,
    AgentState.THINKING,
    AgentState.RUNNING_SHELL,
    AgentState.RUNNING_MCP,
}
_STATE_PRIORITY = {
    AgentState.THINKING: 0,
    AgentState.RUNNING_SHELL: 1,
    AgentState.RUNNING_MCP: 2,
    AgentState.WAITING: 3,
    AgentState.ERROR: 4,
    AgentState.SUCCESS: 5,
    AgentState.IDLE: 6,
}
_SAFE_ID = re.compile(r"[^A-Za-z0-9_.-]+")


def safe_conversation_id(conversation_id: str | None) -> str | None:
    if not conversation_id:
        return None
    cleaned = _SAFE_ID.sub("", conversation_id.strip())[:64]
    return cleaned or None


def is_busy_state(state: str) -> bool:
    try:
        return AgentState(state) in _BUSY_STATES
    except ValueError:
        return False


def _parse_ts(value: str | None) -> float:
    if not value:
        return 0.0
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def pick_auto_focus(sessions: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Pick the session the panel should show by default."""
    live = [session for session in sessions if session.get("active", True)]
    if not live:
        return None

    def sort_key(session: dict[str, Any]) -> tuple[int, float]:
        state = str(session.get("state", AgentState.IDLE.value))
        try:
            priority = _STATE_PRIORITY[AgentState(state)]
        except ValueError:
            priority = 99
        return (priority, -_parse_ts(str(session.get("updated_at") or "")))

    return sorted(live, key=sort_key)[0]


class SessionRegistry:
    """Persist per-conversation status and a registry index on disk."""

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir
        self._registry_path = base_dir / "registry.json"
        self._sessions_dir = base_dir / "sessions"
        self._status_path = base_dir / "status.json"

    @property
    def status_path(self) -> Path:
        return self._status_path

    def publish(self, status: AgentStatus) -> None:
        conversation_id = safe_conversation_id(status.conversation_id)
        registry = self._load_registry()
        sessions: dict[str, dict[str, Any]] = {
            str(item["id"]): dict(item) for item in registry.get("sessions", [])
        }

        if conversation_id:
            entry = self._merge_session_entry(sessions.get(conversation_id), status)
            sessions[conversation_id] = entry
            self._write_json(self._sessions_dir / f"{conversation_id}.json", entry)

        if status.hook_event_name == "sessionEnd" and conversation_id:
            sessions[conversation_id]["active"] = False

        registry_sessions = sorted(
            sessions.values(),
            key=lambda item: _parse_ts(str(item.get("updated_at") or "")),
            reverse=True,
        )
        busy_count = sum(
            1
            for item in registry_sessions
            if item.get("active", True) and is_busy_state(str(item.get("state", "")))
        )
        focused = pick_auto_focus(registry_sessions)
        registry_payload = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "active_count": busy_count,
            "focused_conversation_id": focused.get("id") if focused else None,
            "sessions": registry_sessions,
        }
        self._write_json(self._registry_path, registry_payload)

        focused_status = self._focused_status_payload(status, focused, busy_count)
        self._write_json(self._status_path, focused_status)

    def _merge_session_entry(
        self,
        existing: dict[str, Any] | None,
        status: AgentStatus,
    ) -> dict[str, Any]:
        entry = dict(existing or {})
        entry["id"] = safe_conversation_id(status.conversation_id)
        entry["state"] = status.state.value
        entry["message"] = status.message
        entry["hook_event_name"] = status.hook_event_name
        entry["generation_id"] = status.generation_id
        entry["updated_at"] = status.timestamp
        entry["active"] = entry.get("active", True)

        if status.project:
            entry["project"] = status.project
        elif not entry.get("project"):
            entry["project"] = "workspace"

        if status.label:
            entry["label"] = status.label
        elif not entry.get("label"):
            entry["label"] = entry.get("project", "Agent chat")

        if status.hook_event_name == "sessionStart":
            entry["active"] = True
        if status.hook_event_name == "sessionEnd":
            entry["active"] = False

        entry["metadata"] = status.metadata
        return entry

    def _focused_status_payload(
        self,
        latest: AgentStatus,
        focused: dict[str, Any] | None,
        busy_count: int,
    ) -> dict[str, Any]:
        if focused:
            payload = dict(focused)
            payload["state"] = focused.get("state", latest.state.value)
            payload["message"] = focused.get("message", latest.message)
            payload["hook_event_name"] = focused.get(
                "hook_event_name",
                latest.hook_event_name,
            )
            payload["conversation_id"] = focused.get("id")
            payload["generation_id"] = focused.get("generation_id")
            payload["timestamp"] = focused.get("updated_at", latest.timestamp)
            payload["project"] = focused.get("project")
            payload["label"] = focused.get("label")
            payload["metadata"] = focused.get("metadata", {})
        else:
            payload = latest.to_dict()

        payload["active_count"] = busy_count
        payload["focused_conversation_id"] = focused.get("id") if focused else None
        payload["focus_mode"] = "auto"
        return payload

    def _load_registry(self) -> dict[str, Any]:
        try:
            return json.loads(self._registry_path.read_text(encoding="utf-8"))
        except Exception:
            return {"sessions": []}

    def _write_json(self, path: Path, payload: dict[str, Any]) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = path.with_suffix(path.suffix + ".tmp")
            temp_path.write_text(
                json.dumps(payload, indent=2) + "\n",
                encoding="utf-8",
            )
            temp_path.replace(path)
        except Exception:
            return
