"""Compose configured status sinks."""

from __future__ import annotations

from cursor_agent_beacon.config import BeaconConfig
from cursor_agent_beacon.models import AgentStatus
from cursor_agent_beacon.sinks.base import StatusSink
from cursor_agent_beacon.sinks.file import FileStatusSink
from cursor_agent_beacon.sinks.http import HttpStatusSink
from cursor_agent_beacon.sinks.log import LogStatusSink


class MultiStatusSink:
    """Fan-out sink that swallows individual sink failures."""

    def __init__(self, sinks: list[StatusSink]) -> None:
        self._sinks = sinks

    def publish(self, status: AgentStatus) -> None:
        for sink in self._sinks:
            try:
                sink.publish(status)
            except Exception:
                continue


def build_sinks(config: BeaconConfig | None = None) -> StatusSink:
    config = config or BeaconConfig.from_env()
    sinks: list[StatusSink] = []

    if config.enable_log_sink:
        sinks.append(LogStatusSink())
    if config.enable_file_sink:
        sinks.append(FileStatusSink(config.status_file))
    if config.http_url:
        sinks.append(HttpStatusSink(config.http_url, config.http_timeout_seconds))

    if not sinks:
        sinks.append(LogStatusSink())

    return MultiStatusSink(sinks)
