"""Serial writer: missing port must not crash bridge startup."""

from __future__ import annotations

import time

from cursor_agent_beacon.bridge.serial_writer import QueuedSerialWriter


def test_queued_serial_writer_waits_for_missing_port():
    writer = QueuedSerialWriter(
        "/dev/serial/by-id/does-not-exist-cursor-beacon", 115200
    )
    try:
        writer.write_line("THEME|standard")
        # Give the worker a moment to enter the wait loop (not raise).
        time.sleep(0.3)
        assert writer._thread.is_alive()
        assert writer._serial is None
    finally:
        writer.close()
    assert not writer._thread.is_alive()
