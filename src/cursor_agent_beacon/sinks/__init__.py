"""Compose configured status sinks."""

from __future__ import annotations

import sys

from cursor_agent_beacon.config import BeaconConfig
from cursor_agent_beacon.models import AgentStatus
from cursor_agent_beacon.session_registry import SessionRegistry
from cursor_agent_beacon.sinks.base import StatusSink
from cursor_agent_beacon.sinks.file import FileStatusSink
from cursor_agent_beacon.sinks.http import HttpStatusSink
from cursor_agent_beacon.sinks.log import LogStatusSink


class MultiStatusSink:
    """Fan-out sink that logs individual sink failures without crashing hooks."""

    def __init__(self, sinks: list[StatusSink]) -> None:
        self._sinks = sinks

    def publish(self, status: AgentStatus) -> None:
        for sink in self._sinks:
            try:
                sink.publish(status)
            except Exception as exc:  # noqa: BLE001 - hooks must fail open
                print(
                    f"[cursor-agent-beacon] sink {type(sink).__name__} failed: {exc}",
                    file=sys.stderr,
                    flush=True,
                )


def build_sinks(config: BeaconConfig | None = None) -> StatusSink:
    config = config or BeaconConfig.from_env()
    sinks: list[StatusSink] = []

    registry: SessionRegistry | None = None
    if config.enable_file_sink or config.http_url:
        registry = SessionRegistry(config.status_file.parent)

    if config.enable_log_sink:
        sinks.append(LogStatusSink())
    if registry is not None and config.enable_file_sink:
        sinks.append(FileStatusSink(registry))
    if config.http_url and registry is not None:
        focused = registry.status_path if config.enable_file_sink else None
        sinks.append(
            HttpStatusSink(
                config.http_url,
                config.http_timeout_seconds,
                registry=registry,
                focused_status_file=focused,
            )
        )

    if not sinks:
        sinks.append(LogStatusSink())

    return MultiStatusSink(sinks)
