"""Multi-session registry for cursor-agent-beacon."""

from __future__ import annotations

import json
import re
import sys
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
_SOFT_BUSY_STATES = {AgentState.WAITING, AgentState.THINKING}
_HARD_BUSY_STATES = {AgentState.RUNNING_SHELL, AgentState.RUNNING_MCP}
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
_STALE_SESSION_HOURS = 24
_STALE_BUSY_MINUTES = 10
_STALE_SOFT_BUSY_SEC = 60
_PRUNE_INACTIVE_DAYS = 7
_STALE_STATES = {AgentState.SUCCESS, AgentState.IDLE}


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


def _now_ts() -> float:
    return datetime.now(timezone.utc).timestamp()


def _stale_busy_threshold_sec(session: dict[str, Any]) -> float:
    try:
        state = AgentState(str(session.get("state", "")))
    except ValueError:
        return _STALE_BUSY_MINUTES * 60
    if state in _SOFT_BUSY_STATES:
        return float(_STALE_SOFT_BUSY_SEC)
    return _STALE_BUSY_MINUTES * 60


def _is_stale_busy_session(session: dict[str, Any], now_ts: float) -> bool:
    if not session.get("active", True):
        return False
    if not is_busy_state(str(session.get("state", ""))):
        return False
    age = now_ts - _parse_ts(str(session.get("updated_at") or ""))
    return age >= _stale_busy_threshold_sec(session)


def _latest_hard_busy_ts(
    sessions: list[dict[str, Any]],
) -> float:
    latest = 0.0
    for session in sessions:
        if not session.get("active", True):
            continue
        try:
            state = AgentState(str(session.get("state", "")))
        except ValueError:
            continue
        if state not in _HARD_BUSY_STATES:
            continue
        latest = max(latest, _parse_ts(str(session.get("updated_at") or "")))
    return latest


def _focus_priority(
    session: dict[str, Any],
    *,
    now_ts: float,
    latest_hard_ts: float,
) -> int:
    try:
        state = AgentState(str(session.get("state", AgentState.IDLE.value)))
    except ValueError:
        return 99
    priority = _STATE_PRIORITY[state]
    if state not in _SOFT_BUSY_STATES:
        return priority
    updated = _parse_ts(str(session.get("updated_at") or ""))
    if updated < latest_hard_ts:
        return _STATE_PRIORITY[AgentState.SUCCESS]
    if now_ts - updated >= _STALE_SOFT_BUSY_SEC:
        return _STATE_PRIORITY[AgentState.SUCCESS]
    return priority


def _decay_stale_busy_session(session: dict[str, Any]) -> None:
    """Turn timed-out busy sessions into ready — `stop` hook may never fire."""
    session["state"] = AgentState.SUCCESS.value
    session["message"] = "Ready"
    session.pop("started_at", None)


def _is_stale_session(session: dict[str, Any], now_ts: float) -> bool:
    if not session.get("active", True):
        return False
    if is_busy_state(str(session.get("state", ""))):
        return False
    try:
        state = AgentState(str(session.get("state", AgentState.IDLE.value)))
    except ValueError:
        return False
    if state not in _STALE_STATES:
        return False
    age = now_ts - _parse_ts(str(session.get("updated_at") or ""))
    return age > _STALE_SESSION_HOURS * 3600


def _should_prune_session(session: dict[str, Any], now_ts: float) -> bool:
    if session.get("active", True):
        return False
    age = now_ts - _parse_ts(str(session.get("updated_at") or ""))
    return age > _PRUNE_INACTIVE_DAYS * 86400


def apply_session_housekeeping(
    sessions: dict[str, dict[str, Any]],
    *,
    now_ts: float | None = None,
) -> None:
    """Expire idle sessions and drop long-inactive registry entries."""
    ts = _now_ts() if now_ts is None else now_ts
    for session_id in list(sessions):
        session = sessions[session_id]
        if _should_prune_session(session, ts):
            sessions.pop(session_id, None)
            continue
        if _is_stale_busy_session(session, ts):
            _decay_stale_busy_session(session)
            continue
        if _is_stale_session(session, ts):
            session["active"] = False


def pick_auto_focus(
    sessions: list[dict[str, Any]],
    *,
    now_ts: float | None = None,
) -> dict[str, Any] | None:
    """Pick the session the panel should show by default."""
    ts = _now_ts() if now_ts is None else now_ts
    live = [session for session in sessions if session.get("active", True)]
    if not live:
        return None

    latest_hard_ts = _latest_hard_busy_ts(live)

    def sort_key(session: dict[str, Any]) -> tuple[int, float]:
        priority = _focus_priority(session, now_ts=ts, latest_hard_ts=latest_hard_ts)
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

    def reconcile(self, *, now_ts: float | None = None) -> bool:
        """Re-run housekeeping and refresh status.json.

        Returns True if anything changed.
        """
        registry = self._load_registry()
        sessions: dict[str, dict[str, Any]] = {
            str(item["id"]): dict(item) for item in registry.get("sessions", [])
        }
        if not sessions:
            return False

        before = json.dumps(sessions, sort_keys=True)
        apply_session_housekeeping(sessions, now_ts=now_ts)
        if json.dumps(sessions, sort_keys=True) == before:
            return False

        self._sync_session_files(sessions)
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
        focused_status = self._focused_status_payload(
            AgentStatus(
                state=AgentState.IDLE,
                message="—",
                hook_event_name="reconcile",
            ),
            focused,
            busy_count,
        )
        self._write_json(self._status_path, focused_status)
        return True

    def publish(self, status: AgentStatus) -> None:
        conversation_id = safe_conversation_id(status.conversation_id)
        registry = self._load_registry()
        sessions: dict[str, dict[str, Any]] = {
            str(item["id"]): dict(item) for item in registry.get("sessions", [])
        }

        if conversation_id:
            entry = self._merge_session_entry(sessions.get(conversation_id), status)
            sessions[conversation_id] = entry

        if status.hook_event_name == "sessionEnd" and conversation_id:
            sessions[conversation_id]["active"] = False

        apply_session_housekeeping(sessions)
        self._sync_session_files(sessions)

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
        was_busy = is_busy_state(str(entry.get("state", "")))
        entry["id"] = safe_conversation_id(status.conversation_id)
        entry["state"] = status.state.value
        entry["message"] = status.message
        entry["hook_event_name"] = status.hook_event_name
        entry["generation_id"] = status.generation_id
        entry["updated_at"] = status.timestamp

        if status.hook_event_name == "sessionEnd":
            entry["active"] = False
        else:
            entry["active"] = True

        busy = is_busy_state(status.state.value)
        if busy and not was_busy:
            entry["started_at"] = status.timestamp
        elif not busy and was_busy:
            if entry.get("started_at"):
                entry["last_turn_started_at"] = entry["started_at"]
            entry.pop("started_at", None)

        if status.workspace_root:
            entry["workspace_root"] = status.workspace_root

        if status.project:
            entry["project"] = status.project
        elif not entry.get("project"):
            entry["project"] = "workspace"

        if status.label:
            entry["label"] = status.label
        elif not entry.get("label"):
            entry["label"] = entry.get("project", "Agent chat")

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
        if focused and focused.get("started_at"):
            payload["started_at"] = focused["started_at"]
        return payload

    def _sync_session_files(self, sessions: dict[str, dict[str, Any]]) -> None:
        known = {f"{conv_id}.json" for conv_id in sessions}
        for conv_id, entry in sessions.items():
            self._write_json(self._sessions_dir / f"{conv_id}.json", entry)
        try:
            for path in self._sessions_dir.glob("*.json"):
                if path.name not in known:
                    path.unlink(missing_ok=True)
        except Exception as exc:
            print(
                f"[cursor-agent-beacon] session registry cleanup failed: {exc}",
                file=sys.stderr,
                flush=True,
            )
            return

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
        except Exception as exc:
            print(
                f"[cursor-agent-beacon] session registry write failed ({path}): {exc}",
                file=sys.stderr,
                flush=True,
            )
            return
