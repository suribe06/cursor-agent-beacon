"""Build hook stdout responses that always fail open."""

from __future__ import annotations

import json
from typing import Any

from cursor_agent_beacon.models import HookEvent


def build_hook_response(event: HookEvent) -> dict[str, Any]:
    """Return the minimal JSON response Cursor expects for each hook type."""
    name = event.hook_event_name

    if name in {"beforeShellExecution", "beforeMCPExecution", "subagentStart"}:
        return {"permission": "allow"}

    if name == "beforeSubmitPrompt":
        return {"continue": True}

    if name == "beforeReadFile":
        return {"permission": "allow"}

    if name in {"stop", "subagentStop"}:
        return {}

    return {}


def dump_hook_response(response: dict[str, Any]) -> str:
    return json.dumps(response, separators=(",", ":"))
