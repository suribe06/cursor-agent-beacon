"""Single-owner serial output for ESP32 commands."""

from __future__ import annotations

import queue
import sys
import threading
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
    """Background thread that owns the USB serial port and drains a write queue."""

    def __init__(self, port: str, baud: int) -> None:
        try:
            import serial
        except ImportError as exc:
            raise RuntimeError(
                "pyserial is required for serial output. "
                'Install with: pip install -e ".[bridge]"'
            ) from exc

        self._queue: queue.Queue[str | None] = queue.Queue()
        self._serial = serial.Serial(port, baud, timeout=0.1)
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
        self._serial.close()

    def _run(self) -> None:
        while True:
            line = self._queue.get()
            if line is None:
                return
            try:
                self._serial.write(f"{line}\n".encode())
                self._serial.flush()
            except OSError as exc:
                print(
                    f"[cursor-agent-beacon-bridge] serial write failed: {exc}",
                    file=sys.stderr,
                    flush=True,
                )


def build_serial_writer(
    serial_port: str | None,
    baud: int,
) -> SerialWriter:
    if serial_port:
        return QueuedSerialWriter(serial_port, baud)
    return DryRunSerialWriter()
