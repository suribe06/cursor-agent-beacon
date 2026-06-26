"""Text serial protocol shared by the bridge and VIEWE firmware."""

from __future__ import annotations

from dataclasses import dataclass

from cursor_agent_beacon.compat import StrEnum


class LineKind(StrEnum):
    STATUS = "STATUS"
    THEME = "THEME"
    EVENT = "EVENT"


@dataclass(frozen=True, slots=True)
class StatusCommand:
    state: str
    message: str

    def serial_line(self) -> str:
        safe_message = self.message.replace("|", "/")[:64]
        return f"STATUS|{self.state}|{safe_message}"


@dataclass(frozen=True, slots=True)
class ThemeCommand:
    theme_id: str

    def serial_line(self) -> str:
        return f"THEME|{self.theme_id}"


@dataclass(frozen=True, slots=True)
class EventLine:
    event_type: str

    def serial_line(self) -> str:
        return f"EVENT|{self.event_type}"


def parse_line(raw: str) -> StatusCommand | ThemeCommand | EventLine | None:
    """Parse one protocol line. Returns None for empty or unknown input."""
    line = raw.strip()
    if not line or line.startswith("#"):
        return None

    parts = line.split("|")
    kind = parts[0]

    if kind == LineKind.STATUS and len(parts) >= 3:
        return StatusCommand(state=parts[1], message="|".join(parts[2:]))
    if kind == LineKind.THEME and len(parts) >= 2:
        return ThemeCommand(theme_id=parts[1])
    if kind == LineKind.EVENT and len(parts) >= 2:
        return EventLine(event_type=parts[1])
    return None
