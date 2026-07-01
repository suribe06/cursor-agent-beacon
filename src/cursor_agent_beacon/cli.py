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

    setup_parser = subparsers.add_parser(
        "setup",
        help="Install user hooks and GNOME panel (after pip install)",
    )
    setup_parser.add_argument(
        "--no-gnome",
        action="store_true",
        help="Skip GNOME Shell extension",
    )
    setup_parser.add_argument(
        "--hooks-only",
        action="store_true",
        help="Install user hooks only",
    )
    setup_parser.add_argument(
        "--beacon-bin",
        type=Path,
        default=None,
        help="Path to cursor-agent-beacon executable for the hook wrapper",
    )
    setup_parser.set_defaults(func=_setup)

    doctor_parser = subparsers.add_parser(
        "doctor",
        help="Verify hooks, wrapper, and status directory",
    )
    doctor_parser.add_argument(
        "--probe",
        action="store_true",
        help="Run a sample hook event and verify status.json updates",
    )
    doctor_parser.set_defaults(func=_doctor)

    status_parser = subparsers.add_parser(
        "status",
        help="Show the latest agent status snapshot",
    )
    status_parser.add_argument(
        "--file",
        type=Path,
        default=None,
        help="Status JSON path (default: user status file)",
    )
    status_parser.set_defaults(func=_status)

    uninstall_parser = subparsers.add_parser(
        "uninstall",
        help="Remove user hooks and optional GNOME panel",
    )
    uninstall_parser.add_argument(
        "--hooks-only",
        action="store_true",
        help="Remove hooks only (skip GNOME extension)",
    )
    uninstall_parser.add_argument(
        "--no-gnome",
        action="store_true",
        help="Skip GNOME extension removal",
    )
    uninstall_parser.add_argument(
        "--purge-status",
        action="store_true",
        help="Delete ~/.local/share/cursor-agent-beacon/",
    )
    uninstall_parser.set_defaults(func=_uninstall)

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
    from cursor_agent_beacon.setup import format_next_steps, run_setup

    try:
        result = run_setup()
    except (RuntimeError, FileNotFoundError) as exc:
        print(f"[cursor-agent-beacon] install-desktop failed: {exc}", file=sys.stderr)
        return 1

    print(format_next_steps(result))
    return 0


def _setup(args: argparse.Namespace) -> int:
    from cursor_agent_beacon.setup import format_next_steps, run_setup

    try:
        result = run_setup(
            skip_gnome=args.no_gnome,
            hooks_only=args.hooks_only,
            beacon_bin=args.beacon_bin,
        )
    except (RuntimeError, FileNotFoundError) as exc:
        print(f"[cursor-agent-beacon] setup failed: {exc}", file=sys.stderr)
        return 1

    print(format_next_steps(result))
    return 0


def _doctor(args: argparse.Namespace) -> int:
    from cursor_agent_beacon.doctor import (
        doctor_exit_code,
        format_doctor_report,
        run_doctor,
    )

    results = run_doctor(probe=args.probe)
    print(format_doctor_report(results))
    return doctor_exit_code(results)


def _status(args: argparse.Namespace) -> int:
    from cursor_agent_beacon.doctor import format_status_report, read_status_payload
    from cursor_agent_beacon.install import DEFAULT_STATUS_FILE
    from cursor_agent_beacon.session_registry import SessionRegistry

    path = args.file or DEFAULT_STATUS_FILE
    SessionRegistry(path.parent).reconcile()
    try:
        payload = read_status_payload(path)
    except FileNotFoundError:
        print(
            f"[cursor-agent-beacon] no status at {path}\n"
            "Run an Agent chat in Cursor, or: cursor-agent-beacon doctor --probe",
            file=sys.stderr,
        )
        return 1
    except json.JSONDecodeError as exc:
        print(f"[cursor-agent-beacon] invalid JSON in {path}: {exc}", file=sys.stderr)
        return 1

    print(format_status_report(payload, status_file=path))
    return 0


def _uninstall(args: argparse.Namespace) -> int:
    from cursor_agent_beacon.install import uninstall_desktop

    result = uninstall_desktop(
        hooks_only=args.hooks_only,
        skip_gnome=args.no_gnome,
        keep_status=not args.purge_status,
    )

    lines = ["Uninstall complete.", ""]
    if result["hooks_path"] is not None:
        lines.append(f"Removed hooks from: {result['hooks_path']}")
    else:
        lines.append("Hooks: no beacon entries found")
    if result["gnome_path"] is not None:
        lines.append(f"Removed GNOME panel: {result['gnome_path']}")
    elif not args.hooks_only and not args.no_gnome:
        lines.append("GNOME panel: not installed")
    if result["status_dir"] is not None:
        lines.append(f"Removed status data: {result['status_dir']}")
    lines.append("")
    lines.append("Restart Cursor to stop loading beacon hooks.")
    print("\n".join(lines))
    return 0


class _NullSink:
    def publish(self, status: AgentStatus) -> None:
        return


if __name__ == "__main__":
    raise SystemExit(main())
