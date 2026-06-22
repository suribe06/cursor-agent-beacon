"""Environment-driven configuration for the local bridge service."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def default_bridge_url(host: str = "127.0.0.1", port: int = 8765) -> str:
    return f"http://{host}:{port}/status"


@dataclass(frozen=True, slots=True)
class BridgeConfig:
    """Runtime configuration for the bridge HTTP + serial service."""

    host: str = "127.0.0.1"
    port: int = 8765
    serial_port: str | None = None
    serial_baud: int = 115200
    theme_id: str = "standard"
    themes_dir: Path = Path("themes")

    @property
    def status_url(self) -> str:
        return default_bridge_url(self.host, self.port)

    @classmethod
    def from_env(cls) -> BridgeConfig:
        port_raw = os.environ.get("CURSOR_AGENT_BEACON_BRIDGE_PORT", "8765")
        baud_raw = os.environ.get("CURSOR_AGENT_BEACON_SERIAL_BAUD", "115200")
        serial_port = os.environ.get("CURSOR_AGENT_BEACON_SERIAL_PORT") or None

        try:
            port = int(port_raw)
        except ValueError:
            port = 8765

        try:
            baud = int(baud_raw)
        except ValueError:
            baud = 115200

        return cls(
            host=os.environ.get("CURSOR_AGENT_BEACON_BRIDGE_HOST", "127.0.0.1"),
            port=port,
            serial_port=serial_port,
            serial_baud=baud,
            theme_id=os.environ.get("CURSOR_AGENT_BEACON_THEME", "standard"),
            themes_dir=Path(os.environ.get("CURSOR_AGENT_BEACON_THEMES_DIR", "themes")),
        )
