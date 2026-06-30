"""Environment-driven configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from cursor_agent_beacon.paths import default_themes_dir


def redact_enabled() -> bool:
    return _env_bool("CURSOR_AGENT_BEACON_REDACT_CONTENT", False)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class BeaconConfig:
    """Runtime configuration for the hook handler."""

    enable_log_sink: bool = True
    enable_file_sink: bool = True
    redact_content: bool = False
    status_file: Path = Path(".cursor-agent-beacon/status.json")
    http_url: str | None = None
    http_timeout_seconds: float = 1.0
    theme_id: str = "standard"
    themes_dir: Path = Path("themes")

    @classmethod
    def from_env(cls) -> BeaconConfig:
        status_file = Path(
            os.environ.get(
                "CURSOR_AGENT_BEACON_STATUS_FILE",
                ".cursor-agent-beacon/status.json",
            )
        )
        http_url = os.environ.get("CURSOR_AGENT_BEACON_HTTP_URL") or None
        timeout_raw = os.environ.get("CURSOR_AGENT_BEACON_HTTP_TIMEOUT", "1.0")
        try:
            timeout = float(timeout_raw)
        except ValueError:
            timeout = 1.0

        return cls(
            enable_log_sink=_env_bool("CURSOR_AGENT_BEACON_LOG", True),
            enable_file_sink=_env_bool("CURSOR_AGENT_BEACON_FILE", True),
            redact_content=_env_bool("CURSOR_AGENT_BEACON_REDACT_CONTENT", False),
            status_file=status_file,
            http_url=http_url,
            http_timeout_seconds=timeout,
            theme_id=os.environ.get("CURSOR_AGENT_BEACON_THEME", "standard"),
            themes_dir=default_themes_dir(),
        )
