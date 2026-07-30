"""Map Cursor hook events to normalized agent status."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cursor_agent_beacon.config import redact_enabled
from cursor_agent_beacon.hooks import is_supported_hook
from cursor_agent_beacon.models import (
    AgentState,
    AgentStatus,
    HookEvent,
    parse_model_params,
)

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


def _attachment_summary(attachments: Any) -> tuple[str, dict[str, Any]]:
    """Summarize prompt attachments as '+N files · +M rules'."""
    if not isinstance(attachments, list) or not attachments:
        return "", {}
    files = 0
    rules = 0
    for item in attachments:
        if not isinstance(item, dict):
            files += 1
            continue
        kind = str(item.get("type") or "file").lower()
        if kind == "rule":
            rules += 1
        else:
            files += 1
    bits: list[str] = []
    if files:
        bits.append(f"+{files} file" + ("s" if files != 1 else ""))
    if rules:
        bits.append(f"+{rules} rule" + ("s" if rules != 1 else ""))
    summary = " - ".join(bits)
    return summary, {
        "attachment_count": files + rules,
        "attachment_files": files,
        "attachment_rules": rules,
        "attachments_summary": summary,
    }


def _base_kwargs(
    event: HookEvent, metadata: dict[str, Any] | None = None
) -> dict[str, Any]:
    params = parse_model_params(event.raw.get("model_params"))
    if not params and event.model_params:
        params = {item["id"]: item["value"] for item in event.model_params}
    meta = dict(metadata or {})
    thinking = params.get("thinking")
    if thinking:
        meta["thinking"] = thinking
    context = params.get("context")
    if context:
        meta["context"] = context
    effort = params.get("effort") or None
    model_id = event.model_id or (
        str(event.raw["model_id"]) if event.raw.get("model_id") is not None else None
    )
    return {
        "hook_event_name": event.hook_event_name,
        "conversation_id": event.conversation_id,
        "generation_id": event.generation_id,
        "project": _project_name(event),
        "workspace_root": _workspace_root(event),
        "model": event.model,
        "model_id": model_id,
        "effort": effort,
        "metadata": meta,
    }


def map_hook_event(event: HookEvent) -> AgentStatus | None:
    """Return a normalized status for supported hooks, or None to skip."""
    name = event.hook_event_name
    payload = event.raw

    if name == "sessionStart":
        mode = str(payload.get("composer_mode") or "").strip()
        meta: dict[str, Any] = {"source": "sessionStart"}
        if mode:
            meta["composer_mode"] = mode
        return AgentStatus(
            state=AgentState.IDLE,
            message="Session started",
            label=_project_name(event),
            **_base_kwargs(event, meta),
        )

    if name == "sessionEnd":
        reason = str(payload.get("reason") or "ended")
        return AgentStatus(
            state=AgentState.IDLE,
            message=_truncate(f"Session {reason}"),
            **_base_kwargs(event, {"reason": reason}),
        )

    if name == "beforeSubmitPrompt":
        prompt = str(payload.get("prompt") or "")
        attach_summary, attach_meta = _attachment_summary(payload.get("attachments"))
        if redact_enabled():
            preview = "Processing prompt..."
            label = "Processing prompt..."
        else:
            preview = _truncate(prompt) if prompt else "Processing prompt..."
            label = preview
        if attach_summary:
            # Keep room for the attachment suffix inside the 64-char caption.
            room = _MAX_MESSAGE_LEN - len(attach_summary) - 3
            preview = f"{_truncate(preview, max(12, room))} ({attach_summary})"
        return AgentStatus(
            state=AgentState.WAITING,
            message=preview,
            label=label,
            **_base_kwargs(
                event,
                {"prompt_length": len(prompt), **attach_meta},
            ),
        )

    if name == "afterAgentThought":
        duration_ms = payload.get("duration_ms")
        message = "Thinking..."
        if isinstance(duration_ms, int) and duration_ms > 0:
            message = f"Thinking ({duration_ms}ms)"
        return AgentStatus(
            state=AgentState.THINKING,
            message=message,
            **_base_kwargs(event, {"duration_ms": duration_ms}),
        )

    if name == "beforeShellExecution":
        command = str(payload.get("command") or "")
        meta: dict[str, Any] = {
            "command": command,
            "cwd": payload.get("cwd"),
            "current_tool": "Shell",
        }
        if "sandbox" in payload:
            meta["sandbox"] = bool(payload.get("sandbox"))
        return AgentStatus(
            state=AgentState.RUNNING_SHELL,
            message=_shell_summary(command),
            **_base_kwargs(event, meta),
        )

    if name == "afterShellExecution":
        command = str(payload.get("command") or "")
        failed = _shell_failed(payload)
        meta: dict[str, Any] = {
            "command": command,
            "duration_ms": payload.get("duration"),
            "failed": failed,
            "current_tool": "Shell",
        }
        if "sandbox" in payload:
            meta["sandbox"] = bool(payload.get("sandbox"))
        return AgentStatus(
            state=AgentState.ERROR if failed else AgentState.THINKING,
            message=_shell_summary(command) if failed else "Thinking...",
            **_base_kwargs(event, meta),
        )

    if name == "beforeMCPExecution":
        tool = _mcp_tool_name(payload)
        return AgentStatus(
            state=AgentState.RUNNING_MCP,
            message=f"Tool: {tool}",
            **_base_kwargs(
                event,
                {
                    "tool_name": payload.get("tool_name"),
                    "current_tool": tool,
                },
            ),
        )

    if name == "afterMCPExecution":
        tool = _mcp_tool_name(payload)
        return AgentStatus(
            state=AgentState.THINKING,
            message="Thinking...",
            **_base_kwargs(
                event,
                {
                    "tool_name": payload.get("tool_name"),
                    "last_tool": tool,
                    "current_tool": tool,
                },
            ),
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
            **_base_kwargs(event, {"response_length": len(text)}),
        )

    if name == "beforeReadFile":
        path = str(payload.get("path") or payload.get("file_path") or "")
        if redact_enabled():
            message = "Reading file..."
        else:
            message = _truncate(Path(path).name if path else "Reading file...")
        meta: dict[str, Any] = {"current_tool": "Read"}
        if path and not redact_enabled():
            meta["path"] = path
        return AgentStatus(
            state=AgentState.THINKING,
            message=message,
            **_base_kwargs(event, meta),
        )

    if name == "afterFileEdit":
        path = str(payload.get("file_path") or payload.get("path") or "")
        edits = payload.get("edits") or []
        if redact_enabled():
            message = "Editing file..."
        else:
            name_part = Path(path).name if path else "file"
            message = _truncate(f"Editing {name_part}")
        meta: dict[str, Any] = {
            "edit_count": len(edits) if isinstance(edits, list) else 0,
            "current_tool": "Write",
        }
        if path and not redact_enabled():
            meta["path"] = path
        return AgentStatus(
            state=AgentState.THINKING,
            message=message,
            **_base_kwargs(event, meta),
        )

    if name == "preCompact":
        trigger = str(payload.get("trigger") or "auto")
        meta: dict[str, Any] = {"trigger": trigger}
        pct: float | None = None
        tokens: int | None = None
        window: int | None = None
        raw_pct = payload.get("context_usage_percent")
        raw_tokens = payload.get("context_tokens")
        raw_window = payload.get("context_window_size")
        if raw_pct is not None:
            try:
                pct = float(raw_pct)
                meta["context_usage_percent"] = pct
            except (TypeError, ValueError):
                pct = None
        if raw_tokens is not None:
            try:
                tokens = int(raw_tokens)
                meta["context_tokens"] = tokens
            except (TypeError, ValueError):
                tokens = None
        if raw_window is not None:
            try:
                window = int(raw_window)
                meta["context_window_size"] = window
            except (TypeError, ValueError):
                window = None
        return AgentStatus(
            state=AgentState.THINKING,
            message="Compacting context...",
            context_usage_percent=pct,
            context_tokens=tokens,
            context_window_size=window,
            **_base_kwargs(
                event,
                {**meta, "context_source": "measured"},
            ),
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
            **_base_kwargs(
                event,
                {"stop_status": status, "loop_count": loop_count},
            ),
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
            **_base_kwargs(
                event,
                {"tool_name": tool_name, "current_tool": tool_name},
            ),
        )

    if name == "subagentStart":
        subagent_type = str(payload.get("subagent_type") or "subagent")
        meta: dict[str, Any] = {"subagent_type": subagent_type}
        sub_model = payload.get("subagent_model")
        if isinstance(sub_model, str) and sub_model.strip():
            meta["subagent_model"] = sub_model
        return AgentStatus(
            state=AgentState.THINKING,
            message=_truncate(f"Subagent: {subagent_type}"),
            **_base_kwargs(event, meta),
        )

    if name == "subagentStop":
        # ponytail: parent afterAgentResponse/stop own the panel; subagentStop was
        # leaving chats stuck on Thinking after the visible reply finished.
        return None

    return None
