"""Core hook handler invoked by Cursor."""

from __future__ import annotations

import json
import sys
from typing import Any, TextIO

from cursor_agent_beacon.config import BeaconConfig
from cursor_agent_beacon.mapper import map_hook_event
from cursor_agent_beacon.models import HookEvent
from cursor_agent_beacon.response import build_hook_response, dump_hook_response
from cursor_agent_beacon.sinks import StatusSink, build_sinks


def parse_hook_input(raw_input: str) -> HookEvent:
    payload: dict[str, Any] = json.loads(raw_input or "{}")
    return HookEvent.from_dict(payload)


def handle_hook_event(
    event: HookEvent,
    sink: StatusSink | None = None,
) -> dict[str, Any]:
    """Map the event, publish status, and return the Cursor hook response."""
    status = map_hook_event(event)
    if status is not None:
        active_sink = sink or build_sinks()
        active_sink.publish(status)
    return build_hook_response(event)


def run_hook_handler(
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    sink: StatusSink | None = None,
    config: BeaconConfig | None = None,
) -> int:
    """Entry point used by the Cursor hook script."""
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr

    try:
        raw_input = stdin.read()
        event = parse_hook_input(raw_input)
        active_sink = sink or build_sinks(config)
        response = handle_hook_event(event, sink=active_sink)
        stdout.write(dump_hook_response(response))
        stdout.write("\n")
        stdout.flush()
        return 0
    except json.JSONDecodeError as exc:
        print(
            f"[cursor-agent-beacon] invalid hook JSON: {exc}",
            file=stderr,
            flush=True,
        )
        stdout.write('{"continue": true}\n')
        stdout.flush()
        return 0
    except Exception as exc:  # noqa: BLE001 - hooks must fail open
        print(
            f"[cursor-agent-beacon] handler error: {exc}",
            file=stderr,
            flush=True,
        )
        stdout.write('{"continue": true}\n')
        stdout.flush()
        return 0
