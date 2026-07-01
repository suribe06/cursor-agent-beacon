"""Map Cursor hook events to normalized agent status."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cursor_agent_beacon.config import redact_enabled
from cursor_agent_beacon.hooks import is_supported_hook
from cursor_agent_beacon.models import AgentState, AgentStatus, HookEvent

__all__ = ["map_hook_event", "is_supported_hook"]

_MAX_MESSAGE_LEN = 64
_SHELL_FAILURE_MARKERS = (
    "error:",
    "failed",
    "failure",
    "command not found",
    "permission denied",
    "no such file",
)


def _truncate(text: str, limit: int = _MAX_MESSAGE_LEN) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3] + "..."


def _first_line(text: str) -> str:
    return text.splitlines()[0] if text else ""


def _shell_summary(command: str) -> str:
    command = command.strip()
    if not command:
        return "shell command"
    return _truncate(command)


def _mcp_tool_name(payload: dict[str, Any]) -> str:
    tool_name = str(payload.get("tool_name") or "unknown tool")
    if tool_name.startswith("MCP:"):
        parts = tool_name.split(":")
        if len(parts) >= 3:
            return _truncate(f"{parts[1]}:{parts[2]}")
    return _truncate(tool_name)


def _shell_exit_code(payload: dict[str, Any]) -> int | None:
    for key in ("exit_code", "exitCode", "exit_status", "exitStatus"):
        raw = payload.get(key)
        if raw is None:
            continue
        try:
            return int(raw)
        except (TypeError, ValueError):
            continue
    return None


def _shell_failed(payload: dict[str, Any]) -> bool:
    exit_code = _shell_exit_code(payload)
    if exit_code is not None:
        return exit_code != 0

    output = str(payload.get("output") or "").lower()
    if not output:
        return False
    first_line = _first_line(output).lower()
    if "exit code: 0" in output or "exit_code: 0" in output:
        return False
    return any(marker in first_line for marker in _SHELL_FAILURE_MARKERS)


def _workspace_root(event: HookEvent) -> str | None:
    if event.workspace_roots:
        return event.workspace_roots[0]
    cwd = str(event.raw.get("cwd") or "").strip()
    return cwd or None


def _project_name(event: HookEvent) -> str:
    root = _workspace_root(event)
    if root:
        return Path(root).name or "workspace"
    return "workspace"


def map_hook_event(event: HookEvent) -> AgentStatus | None:
    """Return a normalized status for supported hooks, or None to skip."""
    name = event.hook_event_name
    payload = event.raw
    project = _project_name(event)
    base_kwargs = {
        "hook_event_name": name,
        "conversation_id": event.conversation_id,
        "generation_id": event.generation_id,
        "project": project,
        "workspace_root": _workspace_root(event),
    }

    if name == "sessionStart":
        return AgentStatus(
            state=AgentState.IDLE,
            message="Session started",
            label=project,
            metadata={"source": "sessionStart"},
            **base_kwargs,
        )

    if name == "sessionEnd":
        reason = str(payload.get("reason") or "ended")
        return AgentStatus(
            state=AgentState.IDLE,
            message=_truncate(f"Session {reason}"),
            metadata={"reason": reason},
            **base_kwargs,
        )

    if name == "beforeSubmitPrompt":
        prompt = str(payload.get("prompt") or "")
        if redact_enabled():
            preview = "Processing prompt..."
            label = "Processing prompt..."
        else:
            preview = _truncate(prompt) if prompt else "Processing prompt..."
            label = preview
        return AgentStatus(
            state=AgentState.WAITING,
            message=preview,
            label=label,
            metadata={"prompt_length": len(prompt)},
            **base_kwargs,
        )

    if name == "afterAgentThought":
        duration_ms = payload.get("duration_ms")
        message = "Thinking..."
        if isinstance(duration_ms, int) and duration_ms > 0:
            message = f"Thinking ({duration_ms}ms)"
        return AgentStatus(
            state=AgentState.THINKING,
            message=message,
            metadata={"duration_ms": duration_ms},
            **base_kwargs,
        )

    if name == "beforeShellExecution":
        command = str(payload.get("command") or "")
        return AgentStatus(
            state=AgentState.RUNNING_SHELL,
            message=_shell_summary(command),
            metadata={"command": command, "cwd": payload.get("cwd")},
            **base_kwargs,
        )

    if name == "afterShellExecution":
        command = str(payload.get("command") or "")
        failed = _shell_failed(payload)
        return AgentStatus(
            state=AgentState.ERROR if failed else AgentState.THINKING,
            message=_shell_summary(command) if failed else "Thinking...",
            metadata={
                "command": command,
                "duration_ms": payload.get("duration"),
                "failed": failed,
            },
            **base_kwargs,
        )

    if name == "beforeMCPExecution":
        tool = _mcp_tool_name(payload)
        return AgentStatus(
            state=AgentState.RUNNING_MCP,
            message=f"Tool: {tool}",
            metadata={"tool_name": payload.get("tool_name")},
            **base_kwargs,
        )

    if name == "afterMCPExecution":
        tool = _mcp_tool_name(payload)
        return AgentStatus(
            state=AgentState.THINKING,
            message="Thinking...",
            metadata={"tool_name": payload.get("tool_name"), "last_tool": tool},
            **base_kwargs,
        )

    if name == "afterAgentResponse":
        text = str(payload.get("text") or "")
        if redact_enabled():
            preview = "Ready"
        else:
            preview = _truncate(text) if text else "Ready"
        return AgentStatus(
            state=AgentState.SUCCESS,
            message=preview,
            metadata={"response_length": len(text)},
            **base_kwargs,
        )

    if name == "beforeReadFile":
        path = str(payload.get("path") or payload.get("file_path") or "")
        if redact_enabled():
            message = "Reading file..."
        else:
            message = _truncate(Path(path).name if path else "Reading file...")
        return AgentStatus(
            state=AgentState.THINKING,
            message=message,
            metadata={"path": path} if path and not redact_enabled() else {},
            **base_kwargs,
        )

    if name == "afterFileEdit":
        path = str(payload.get("file_path") or payload.get("path") or "")
        edits = payload.get("edits") or []
        if redact_enabled():
            message = "Editing file..."
        else:
            name_part = Path(path).name if path else "file"
            message = _truncate(f"Editing {name_part}")
        return AgentStatus(
            state=AgentState.THINKING,
            message=message,
            metadata={
                "path": path,
                "edit_count": len(edits) if isinstance(edits, list) else 0,
            }
            if path and not redact_enabled()
            else {"edit_count": len(edits) if isinstance(edits, list) else 0},
            **base_kwargs,
        )

    if name == "preCompact":
        trigger = str(payload.get("trigger") or "auto")
        return AgentStatus(
            state=AgentState.THINKING,
            message="Compacting context...",
            metadata={"trigger": trigger},
            **base_kwargs,
        )

    if name == "stop":
        status = str(payload.get("status") or "completed")
        loop_count = payload.get("loop_count")
        if status == "error":
            state = AgentState.ERROR
            message = "Agent stopped with error"
        elif status == "aborted":
            state = AgentState.IDLE
            message = "Agent aborted"
        else:
            state = AgentState.SUCCESS
            message = "Ready"
        return AgentStatus(
            state=state,
            message=message,
            metadata={"stop_status": status, "loop_count": loop_count},
            **base_kwargs,
        )

    if name in {"preToolUse", "postToolUse", "postToolUseFailure"}:
        tool_name = str(payload.get("tool_name") or "tool")
        if name == "preToolUse":
            state = AgentState.WAITING
            message = f"Using {tool_name}"
        elif name == "postToolUseFailure":
            failure_type = str(payload.get("failure_type") or "")
            if failure_type == "permission_denied":
                state = AgentState.WAITING
                message = f"Denied: {tool_name}"
            else:
                state = AgentState.ERROR
                message = f"Failed: {tool_name}"
        else:
            # ponytail: turn not done until `stop`; agent thinks again after each tool
            state = AgentState.THINKING
            message = "Thinking..."
        return AgentStatus(
            state=state,
            message=_truncate(message),
            metadata={"tool_name": tool_name},
            **base_kwargs,
        )

    if name == "subagentStart":
        subagent_type = str(payload.get("subagent_type") or "subagent")
        return AgentStatus(
            state=AgentState.THINKING,
            message=_truncate(f"Subagent: {subagent_type}"),
            metadata={"subagent_type": subagent_type},
            **base_kwargs,
        )

    if name == "subagentStop":
        return AgentStatus(
            state=AgentState.THINKING,
            message="Thinking...",
            metadata={"status": payload.get("status")},
            **base_kwargs,
        )

    return None
