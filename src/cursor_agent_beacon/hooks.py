"""Cursor hooks mapped to agent status — single source of truth."""

from __future__ import annotations

SUPPORTED_HOOKS: tuple[str, ...] = (
    "sessionStart",
    "sessionEnd",
    "beforeSubmitPrompt",
    "afterAgentThought",
    "beforeShellExecution",
    "afterShellExecution",
    "beforeMCPExecution",
    "afterMCPExecution",
    "afterAgentResponse",
    "stop",
    "preToolUse",
    "postToolUse",
    "postToolUseFailure",
    "subagentStart",
    "subagentStop",
    "beforeReadFile",
    "afterFileEdit",
    "preCompact",
)


def is_supported_hook(hook_event_name: str) -> bool:
    """Return True when the hook is mapped to a status update."""
    return hook_event_name in SUPPORTED_HOOKS
