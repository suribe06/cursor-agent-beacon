"""Text serial protocol shared by the bridge and VIEWE firmware."""

from __future__ import annotations

from dataclasses import dataclass

from cursor_agent_beacon.compat import StrEnum


class LineKind(StrEnum):
    STATUS = "STATUS"
    THEME = "THEME"
    EVENT = "EVENT"


def _ascii_field(text: str, limit: int) -> str:
    """Keep serial captions firmware-safe (Montserrat is ASCII-ish)."""
    cleaned = (
        text.replace("|", "/").replace("·", "-").replace("—", "-").replace("–", "-")
    )
    cleaned = "".join(ch if 32 <= ord(ch) < 127 else " " for ch in cleaned)
    cleaned = " ".join(cleaned.split())
    return cleaned[:limit]


@dataclass(frozen=True, slots=True)
class StatusCommand:
    state: str
    message: str
    model: str = ""
    context_pct: int | None = None

    def serial_line(self) -> str:
        safe_message = _ascii_field(self.message, 64)
        safe_model = _ascii_field(self.model, 48) if self.model else ""
        if self.context_pct is not None:
            pct = max(0, min(100, int(self.context_pct)))
            return f"STATUS|{self.state}|{safe_message}|{safe_model}|{pct}"
        if safe_model:
            return f"STATUS|{self.state}|{safe_message}|{safe_model}"
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
        model = ""
        context_pct = None
        if len(parts) >= 5:
            message = parts[2]
            model = parts[3]
            try:
                context_pct = int(parts[4])
            except ValueError:
                context_pct = None
        elif len(parts) >= 4:
            message = parts[2]
            model = parts[3]
        else:
            message = "|".join(parts[2:])
        return StatusCommand(
            state=parts[1],
            message=message,
            model=model,
            context_pct=context_pct,
        )
    if kind == LineKind.THEME and len(parts) >= 2:
        return ThemeCommand(theme_id=parts[1])
    if kind == LineKind.EVENT and len(parts) >= 2:
        return EventLine(event_type=parts[1])
    return None
