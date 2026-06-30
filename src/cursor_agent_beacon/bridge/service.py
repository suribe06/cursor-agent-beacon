"""Bridge business logic: theme resolution and serial command emission."""

from __future__ import annotations

import threading
from typing import Any

from cursor_agent_beacon.bridge.config import BridgeConfig
from cursor_agent_beacon.bridge.serial_writer import SerialWriter, build_serial_writer
from cursor_agent_beacon.models import AgentStatus
from cursor_agent_beacon.theme import ThemePack, load_theme


class BridgeService:
    """Resolve theme GIFs and forward normalized status to the serial writer."""

    def __init__(
        self,
        config: BridgeConfig,
        theme: ThemePack | None = None,
        serial_writer: SerialWriter | None = None,
    ) -> None:
        self._config = config
        self._theme = theme or load_theme(config.theme_id, config.themes_dir)
        self._serial = serial_writer or build_serial_writer(
            config.serial_port,
            config.serial_baud,
        )
        self._lock = threading.Lock()
        self._latest: AgentStatus | None = None
        self._serial.write_line(f"THEME|{self._theme.theme_id}")

    @property
    def config(self) -> BridgeConfig:
        return self._config

    @property
    def theme(self) -> ThemePack:
        return self._theme

    @property
    def latest_status(self) -> AgentStatus | None:
        return self._latest

    def close(self) -> None:
        self._serial.close()

    def handle_status(self, payload: dict[str, Any]) -> dict[str, Any]:
        status = AgentStatus.from_dict(payload)
        animation = self._theme.animation_for(
            status.state.value,
            hook_event_name=status.hook_event_name,
        )

        serial_line = status.serial_line()
        self._serial.write_line(serial_line)

        with self._lock:
            self._latest = status

        gif_path: str | None = None
        if animation is not None:
            try:
                gif_path = str(animation.path.relative_to(self._theme.root))
            except ValueError:
                gif_path = str(animation.path)

        return {
            "ok": True,
            "serial": serial_line,
            "theme_id": self._theme.theme_id,
            "state": status.state.value,
            "message": status.message,
            "gif": gif_path,
            "caption": animation.caption if animation else None,
            "loop": animation.loop if animation else None,
        }

    def health(self) -> dict[str, Any]:
        latest = self._latest
        return {
            "ok": True,
            "theme_id": self._theme.theme_id,
            "serial_port": self._config.serial_port,
            "serial_baud": self._config.serial_baud,
            "status_url": self._config.status_url,
            "latest": latest.to_dict() if latest else None,
        }
