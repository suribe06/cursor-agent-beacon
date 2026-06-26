"""CLI utilities for local testing."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cursor_agent_beacon.handler import (
    handle_hook_event,
    parse_hook_input,
    run_hook_handler,
)
from cursor_agent_beacon.mapper import map_hook_event
from cursor_agent_beacon.models import AgentStatus


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Cursor Agent Beacon hook utilities",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser(
        "run",
        help="Run the hook handler (reads JSON from stdin)",
    )
    run_parser.set_defaults(func=_run_handler)

    map_parser = subparsers.add_parser(
        "map",
        help="Map a sample hook JSON file to agent status",
    )
    map_parser.add_argument("event_file", type=Path)
    map_parser.set_defaults(func=_map_event)

    bridge_parser = subparsers.add_parser(
        "bridge",
        help="Run the local HTTP + serial bridge service (Phase 2)",
    )
    bridge_parser.set_defaults(func=_run_bridge)

    args = parser.parse_args()
    return int(args.func(args))


def _run_handler(_args: argparse.Namespace) -> int:
    return run_hook_handler()


def _map_event(args: argparse.Namespace) -> int:
    payload = json.loads(args.event_file.read_text(encoding="utf-8"))
    event = parse_hook_input(json.dumps(payload))
    status = map_hook_event(event)
    response = handle_hook_event(event, sink=_NullSink())

    if status is None:
        print("No status mapping for this hook.", file=sys.stderr)
        return 1

    print(json.dumps(status.to_dict(), indent=2))
    print(json.dumps(response, indent=2))
    return 0


def _run_bridge(_args: argparse.Namespace) -> int:
    from cursor_agent_beacon.bridge.config import BridgeConfig
    from cursor_agent_beacon.bridge.server import run_bridge_server
    from cursor_agent_beacon.bridge.service import BridgeService

    config = BridgeConfig.from_env()
    service = BridgeService(config)
    run_bridge_server(service, config.host, config.port)
    return 0


class _NullSink:
    def publish(self, status: AgentStatus) -> None:
        return


if __name__ == "__main__":
    raise SystemExit(main())
