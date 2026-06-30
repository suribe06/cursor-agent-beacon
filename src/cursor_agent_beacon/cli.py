"""CLI utilities for local testing and installation."""

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
        help="Run the local HTTP + serial bridge service",
    )
    bridge_parser.set_defaults(func=_run_bridge)

    install_hooks = subparsers.add_parser(
        "install-hooks",
        help="Install merge-safe user-level Cursor hooks",
    )
    install_hooks.set_defaults(func=_install_hooks)

    install_gnome = subparsers.add_parser(
        "install-gnome",
        help="Install the GNOME Shell status panel extension",
    )
    install_gnome.set_defaults(func=_install_gnome)

    install_desktop = subparsers.add_parser(
        "install-desktop",
        help="Install user hooks and GNOME panel",
    )
    install_desktop.set_defaults(func=_install_desktop)

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


def _install_hooks(_args: argparse.Namespace) -> int:
    from cursor_agent_beacon.install import verify_package_installed, write_user_hooks

    try:
        verify_package_installed()
        hooks_path = write_user_hooks()
    except (RuntimeError, FileNotFoundError) as exc:
        print(f"[cursor-agent-beacon] install-hooks failed: {exc}", file=sys.stderr)
        return 1

    print(f"Hooks: {hooks_path}")
    print("Restart Cursor after install.")
    return 0


def _install_gnome(_args: argparse.Namespace) -> int:
    from cursor_agent_beacon.install import install_gnome_extension

    try:
        dest = install_gnome_extension()
    except FileNotFoundError as exc:
        print(f"[cursor-agent-beacon] install-gnome failed: {exc}", file=sys.stderr)
        return 1

    print(f"GNOME extension: {dest}")
    print("Reload GNOME Shell if the panel does not update.")
    return 0


def _install_desktop(_args: argparse.Namespace) -> int:
    from cursor_agent_beacon.install import install_desktop, verify_package_installed

    try:
        verify_package_installed()
        hooks_path, ext_path = install_desktop()
    except (RuntimeError, FileNotFoundError) as exc:
        print(f"[cursor-agent-beacon] install-desktop failed: {exc}", file=sys.stderr)
        return 1

    print(f"Hooks: {hooks_path}")
    print(f"GNOME extension: {ext_path}")
    print("Restart Cursor and reload GNOME Shell.")
    return 0


class _NullSink:
    def publish(self, status: AgentStatus) -> None:
        return


if __name__ == "__main__":
    raise SystemExit(main())
