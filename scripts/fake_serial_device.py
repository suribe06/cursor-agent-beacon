#!/usr/bin/env python3
"""Virtual VIEWE display for testing the bridge without hardware.

Creates a pseudo-TTY pair. Point the bridge at the slave port; this script
reads STATUS/THEME lines and prints what the display would show.

Usage:
  # Terminal 1
  python3 scripts/fake_serial_device.py

  # Terminal 2
  export CURSOR_AGENT_BEACON_SERIAL_PORT=/dev/pts/N   # printed by script
  export CURSOR_AGENT_BEACON_SERIAL_BAUD=115200
  cursor-agent-beacon bridge

  # Terminal 3
  export CURSOR_AGENT_BEACON_HTTP_URL=http://127.0.0.1:8765/status
  python3 scripts/simulate_hook.py examples/sample-events/after_agent_thought.json
"""

from __future__ import annotations

import argparse
import os
import select
import sys
import termios
import tty
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cursor_agent_beacon.protocol import (
    EventLine,
    StatusCommand,
    ThemeCommand,
    parse_line,
)


def _open_pty_pair() -> tuple[int, str]:
    import pty

    master, slave = pty.openpty()
    slave_name = os.ttyname(slave)
    return master, slave_name


def _format_status(cmd: StatusCommand) -> str:
    return f"[DISPLAY] state={cmd.state!r} message={cmd.message!r}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Fake VIEWE serial display")
    parser.add_argument(
        "--emit-on-enter",
        action="store_true",
        help="Press Enter to emit EVENT|button_pressed (simulates knob button)",
    )
    args = parser.parse_args()

    master_fd, slave_path = _open_pty_pair()
    print(f"[fake-display] Bridge serial port: {slave_path}", flush=True)
    print(
        "[fake-display] Baud default: 115200 (set CURSOR_AGENT_BEACON_SERIAL_BAUD)",
        flush=True,
    )
    print("[fake-display] Waiting for STATUS lines... (Ctrl+C to quit)", flush=True)

    buffer = ""
    old_tty = (
        termios.tcgetattr(sys.stdin)
        if args.emit_on_enter and sys.stdin.isatty()
        else None
    )
    if old_tty is not None:
        tty.setcbreak(sys.stdin.fileno())

    try:
        while True:
            read_fds = [master_fd]
            if args.emit_on_enter and sys.stdin.isatty():
                read_fds.append(sys.stdin)
            ready, _, _ = select.select(read_fds, [], [], 0.2)

            if master_fd in ready:
                chunk = os.read(master_fd, 4096).decode("utf-8", errors="replace")
                if not chunk:
                    break
                buffer += chunk
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    parsed = parse_line(line)
                    if isinstance(parsed, StatusCommand):
                        print(_format_status(parsed), flush=True)
                    elif isinstance(parsed, ThemeCommand):
                        print(f"[DISPLAY] theme={parsed.theme_id!r}", flush=True)
                    elif parsed is not None:
                        print(f"[DISPLAY] ignored {line!r}", flush=True)

            if args.emit_on_enter and sys.stdin in ready:
                ch = sys.stdin.read(1)
                if ch in {"\n", "\r"}:
                    event = EventLine(event_type="button_pressed")
                    os.write(master_fd, f"{event.serial_line()}\n".encode())
                    print("[fake-display] sent EVENT|button_pressed", flush=True)
    except KeyboardInterrupt:
        print("\n[fake-display] stopped", flush=True)
    finally:
        if old_tty is not None:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_tty)
        os.close(master_fd)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
