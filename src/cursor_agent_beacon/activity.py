"""Append-only activity log for one Cursor conversation.

shortcut: the hook rewrites the file when it crosses the cap. Move rotation
off the hook path if that rewrite shows up in handler time.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

from cursor_agent_beacon.models import AgentStatus, HookEvent
from cursor_agent_beacon.session_registry import safe_conversation_id
from cursor_agent_beacon.stations import STATION_ORDER, classify, phase_of

MAX_LINES = 5000
MAX_BYTES = 2 * 1024 * 1024
PRUNE_DAYS = 7

_START_END = {
    "beforeShellExecution",
    "afterShellExecution",
    "beforeMCPExecution",
    "afterMCPExecution",
    "preToolUse",
    "postToolUse",
    "postToolUseFailure",
    "beforeReadFile",
    "afterFileEdit",
    "subagentStart",
    "subagentStop",
    "sessionStart",
    "sessionEnd",
}


def append_activity(
    event: HookEvent,
    status: AgentStatus | None,
    *,
    root: Path,
    redact: bool = False,
    max_lines: int = MAX_LINES,
    max_bytes: int = MAX_BYTES,
) -> None:
    """Write one JSON line. I/O errors are logged and swallowed."""
    if status is None and event.hook_event_name != "subagentStop":
        return
    try:
        path = _path_for(root, event.conversation_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(
            _record(event, status, redact=redact),
            ensure_ascii=True,
            separators=(",", ":"),
        )
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
        _trim(path, max_lines=max_lines, max_bytes=max_bytes)
        _write_summary(root, json.loads(line))
        _prune(root)
    except Exception as exc:  # noqa: BLE001 - hooks must fail open
        print(
            f"[cursor-agent-beacon] activity log failed: {exc}",
            file=sys.stderr,
            flush=True,
        )


def _flag(record: dict[str, Any]) -> str:
    detail = record.get("detail") or {}
    failed = (
        record.get("state") == "error"
        or detail.get("denied") is True
        or record.get("station") == "hooks"
    )
    if record.get("phase") == "end" and not failed:
        return "0"
    return "2" if failed else "1"


def _write_summary(root: Path, record: dict[str, Any]) -> None:
    """Cache the panel and the desk display both read. Not a second log."""
    cid = record.get("conversation_id") or "unknown"
    path = root / "events" / f"{cid}.summary.json"
    stations = {name: "0" for name in STATION_ORDER}
    if path.is_file():
        try:
            saved = json.loads(path.read_text(encoding="utf-8")).get("stations") or {}
        except (OSError, json.JSONDecodeError):
            saved = {}
        for name in STATION_ORDER:
            value = str(saved.get(name, "0"))
            if value in {"0", "1", "2"}:
                stations[name] = value
    station = str(record.get("station") or "")
    if station in stations:
        stations[station] = _flag(record)
    flags = "".join(stations[name] for name in STATION_ORDER)
    payload = {
        "conversation_id": cid,
        "label": str(record.get("label") or "")[:32],
        "flags": flags,
        "stations": stations,
    }
    path.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")


def _path_for(root: Path, conversation_id: str | None) -> Path:
    safe = safe_conversation_id(conversation_id) or "unknown"
    return root / "events" / f"{safe}.jsonl"


def _record(
    event: HookEvent,
    status: AgentStatus | None,
    *,
    redact: bool,
) -> dict[str, Any]:
    raw = event.raw
    command = str(raw.get("command") or "")
    tool = str(raw.get("tool_name") or "")
    denied = _denied(raw)
    station = classify(event.hook_event_name, command=command, tool=tool, denied=denied)
    record: dict[str, Any] = {
        "schema": 1,
        "ts": status.timestamp if status is not None else _now(),
        "conversation_id": safe_conversation_id(event.conversation_id),
        "generation_id": event.generation_id,
        "source": "cursor",
        "hook_event_name": event.hook_event_name,
        "station": station,
        "phase": phase_of(event.hook_event_name),
        "call_id": _call_id(event, station),
        "state": status.state.value if status is not None else "idle",
        "label": station if redact else _label(status, event),
        "detail": {} if redact else _detail(event, denied=denied),
        "redacted": redact,
    }
    if status is not None:
        if status.model:
            record["model"] = status.model
        if status.model_id:
            record["model_id"] = status.model_id
        if status.effort:
            record["effort"] = status.effort
        if status.context_usage_percent is not None:
            record["context_usage_percent"] = status.context_usage_percent
    return record


def _now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _label(status: AgentStatus | None, event: HookEvent) -> str:
    if status is not None and status.message:
        return status.message[:80]
    return event.hook_event_name


def _denied(raw: dict[str, Any]) -> bool:
    if raw.get("failure_type") == "permission_denied":
        return True
    return bool(raw.get("denied"))


def _call_id(event: HookEvent, station: str) -> str | None:
    raw = event.raw
    for key in ("call_id", "tool_call_id", "toolCallId"):
        value = raw.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()[:64]
    if event.hook_event_name not in _START_END:
        return None
    cid = safe_conversation_id(event.conversation_id) or "unknown"
    gid = str(event.generation_id or "")[:32]
    return f"{cid}:{gid}:{station}:{_slug(event)}"[:96]


def _slug(event: HookEvent) -> str:
    raw = event.raw
    hook = event.hook_event_name
    if "Shell" in hook:
        words = str(raw.get("command") or "").split()
        return (words[0] if words else "cmd")[:40]
    if hook in {"preToolUse", "postToolUse", "postToolUseFailure"} or "MCP" in hook:
        return str(raw.get("tool_name") or "tool")[:40]
    if hook in {"beforeReadFile", "afterFileEdit"}:
        path = str(raw.get("path") or raw.get("file_path") or "file")
        return Path(path).name[:40]
    if hook.startswith("subagent"):
        return str(raw.get("subagent_type") or "sub")[:40]
    return hook[:40]


def _detail(event: HookEvent, *, denied: bool) -> dict[str, Any]:
    raw = event.raw
    hook = event.hook_event_name
    detail: dict[str, Any] = {}
    tool = raw.get("tool_name")
    if isinstance(tool, str) and tool:
        detail["tool"] = tool[:80]
        if "MCP" in hook:
            parts = tool.split(":")
            if len(parts) >= 2:
                detail["mcp_server"] = parts[1][:80]
    if hook in {"beforeReadFile", "afterFileEdit"}:
        path = raw.get("path") or raw.get("file_path")
        if path:
            detail["path"] = Path(str(path)).name[:80]
    if "Shell" in hook:
        words = str(raw.get("command") or "").split()
        if words:
            detail["command"] = words[0][:40]
    if hook == "afterShellExecution" and raw.get("exit_code") is not None:
        try:
            detail["exit_status"] = int(raw["exit_code"])
        except (TypeError, ValueError):
            pass
    sub = raw.get("subagent_type")
    if isinstance(sub, str) and sub:
        detail["subagent_type"] = sub[:40]
    if denied:
        detail["denied"] = True
    return detail


def _trim(path: Path, *, max_lines: int, max_bytes: int) -> None:
    size = path.stat().st_size
    if size <= max_bytes and size // 40 <= max_lines:
        return
    lines = path.read_text(encoding="utf-8").splitlines()
    keep = lines[-max_lines:]
    while keep and sum(len(line) + 1 for line in keep) > max_bytes:
        keep = keep[len(keep) // 2 :]
    path.write_text("\n".join(keep) + ("\n" if keep else ""), encoding="utf-8")


def _prune(root: Path) -> None:
    events = root / "events"
    registry_path = root / "registry.json"
    if not events.is_dir() or not registry_path.is_file():
        return
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    keep = {
        str(item.get("id"))
        for item in registry.get("sessions") or []
        if isinstance(item, dict) and item.get("id")
    }
    cutoff = time.time() - PRUNE_DAYS * 86400
    for path in events.glob("*.jsonl"):
        if path.stem in keep:
            continue
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink()
        except OSError:
            continue
