"""Local bridge service: HTTP status intake and serial output for ESP32."""

from cursor_agent_beacon.bridge.config import BridgeConfig
from cursor_agent_beacon.bridge.server import run_bridge_server
from cursor_agent_beacon.bridge.service import BridgeService

__all__ = ["BridgeConfig", "BridgeService", "run_bridge_server"]
