"""Single-owner serial output for ESP32 commands."""

from __future__ import annotations

import queue
import sys
import threading
import time
from typing import Protocol


class SerialWriter(Protocol):
    def write_line(self, line: str) -> None: ...

    def close(self) -> None: ...


class DryRunSerialWriter:
    """Log serial lines to stderr when no hardware port is configured."""

    def write_line(self, line: str) -> None:
        print(
            f"[cursor-agent-beacon-bridge] serial: {line}",
            file=sys.stderr,
            flush=True,
        )

    def close(self) -> None:
        return


class QueuedSerialWriter:
    """Background thread that owns the USB serial port and drains a write queue.

    If the port is missing (device unplugged), keep the bridge up and retry
    until it appears — no crash loop.
    """

    _RETRY_SEC = 5.0

    def __init__(self, port: str, baud: int) -> None:
        try:
            import serial  # noqa: F401
        except ImportError as exc:
            raise RuntimeError(
                "pyserial is required for serial output. "
                'Install with: pip install -e ".[bridge]"'
            ) from exc

        self._port = port
        self._baud = baud
        self._queue: queue.Queue[str | None] = queue.Queue()
        self._serial = None
        self._closed = False
        self._thread = threading.Thread(
            target=self._run,
            name="cursor-agent-beacon-serial",
            daemon=True,
        )
        self._thread.start()

    def write_line(self, line: str) -> None:
        if self._closed:
            return
        self._queue.put(line)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._queue.put(None)
        self._thread.join(timeout=2.0)
        self._close_serial()

    def _close_serial(self) -> None:
        ser = self._serial
        self._serial = None
        if ser is not None:
            try:
                ser.close()
            except OSError:
                pass

    def _open_serial(self):
        import serial

        last_log = 0.0
        while not self._closed:
            try:
                self._serial = serial.Serial(self._port, self._baud, timeout=0.1)
                print(
                    f"[cursor-agent-beacon-bridge] serial open: {self._port}",
                    file=sys.stderr,
                    flush=True,
                )
                return
            except (OSError, serial.SerialException) as exc:
                now = time.monotonic()
                # ponytail: journal spam ceiling = 1 line / 60s while unplugged
                if now - last_log >= 60.0:
                    print(
                        f"[cursor-agent-beacon-bridge] waiting for {self._port}: {exc}",
                        file=sys.stderr,
                        flush=True,
                    )
                    last_log = now
                deadline = now + self._RETRY_SEC
                while not self._closed and time.monotonic() < deadline:
                    time.sleep(0.2)

    def _run(self) -> None:
        import serial

        while True:
            line = self._queue.get()
            if line is None:
                return
            if self._serial is None:
                self._open_serial()
                if self._serial is None:
                    return
            try:
                # Drain device TX (boot logs / accidental echo) so it never
                # piles up on the host side of the CDC port.
                waiting = getattr(self._serial, "in_waiting", 0) or 0
                if waiting:
                    self._serial.read(waiting)
                self._serial.write(f"{line}\n".encode("ascii", "replace"))
                self._serial.flush()
            except (OSError, serial.SerialException) as exc:
                print(
                    f"[cursor-agent-beacon-bridge] serial write failed: {exc}",
                    file=sys.stderr,
                    flush=True,
                )
                self._close_serial()


def build_serial_writer(
    serial_port: str | None,
    baud: int,
) -> SerialWriter:
    if serial_port:
        return QueuedSerialWriter(serial_port, baud)
    return DryRunSerialWriter()
