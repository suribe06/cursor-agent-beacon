"""User display preferences for VIEWE + GNOME panel.

File (created once by ``setup``, never overwritten):

    ~/.config/cursor-agent-beacon/display.toml

Shared ``[show]`` toggles apply to both surfaces; ``[extension].panel_badge``
only controls the top-bar percent badge.
"""

from __future__ import annotations

import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

_BOOL = re.compile(r"^(true|false)$", re.IGNORECASE)
_KEY = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+?)\s*(?:#.*)?$")

DEFAULT_CONFIG_DIR = Path.home() / ".config" / "cursor-agent-beacon"
DEFAULT_DISPLAY_CONFIG = DEFAULT_CONFIG_DIR / "display.toml"

_DEFAULT_TOML = """\
# Cursor Agent Beacon — what to show on the VIEWE display and GNOME panel.
# Edit and save; then run: cursor-agent-beacon reload
# `cursor-agent-beacon setup` creates this file once and will not overwrite it.

[show]
model = true
effort = true
context = true
message = true
attachments = true
sandbox = true

[extension]
panel_badge = true
"""

_SHOW_KEYS = (
    "model",
    "effort",
    "context",
    "message",
    "attachments",
    "sandbox",
)
_CACHE: tuple[float | None, DisplayPrefs] | None = None


@dataclass(frozen=True, slots=True)
class DisplayPrefs:
    """What the user wants visible on beacon surfaces."""

    model: bool = True
    effort: bool = True
    context: bool = True
    message: bool = True
    attachments: bool = True
    sandbox: bool = True
    panel_badge: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "show": {
                "model": self.model,
                "effort": self.effort,
                "context": self.context,
                "message": self.message,
                "attachments": self.attachments,
                "sandbox": self.sandbox,
            },
            "extension": {"panel_badge": self.panel_badge},
        }

    def model_caption(self, model_label: str | None, effort: str | None) -> str:
        bits: list[str] = []
        if self.model and model_label:
            bits.append(model_label)
        if self.effort and effort:
            bits.append(effort)
        return " ".join(bits)


def display_config_path() -> Path:
    override = os.environ.get("CURSOR_AGENT_BEACON_DISPLAY_CONFIG")
    if override:
        return Path(override)
    return DEFAULT_DISPLAY_CONFIG


def default_display_prefs() -> DisplayPrefs:
    return DisplayPrefs()


def ensure_display_config(path: Path | None = None) -> Path:
    """Create the default display.toml if missing. Never overwrite."""
    target = path or display_config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.is_file():
        target.write_text(_DEFAULT_TOML, encoding="utf-8")
    return target


def load_display_prefs(
    path: Path | None = None, *, use_cache: bool = True
) -> DisplayPrefs:
    """Load prefs from disk; missing/invalid file → defaults."""
    global _CACHE
    target = path or display_config_path()
    mtime: float | None
    try:
        mtime = target.stat().st_mtime
    except OSError:
        mtime = None

    if use_cache and _CACHE is not None and _CACHE[0] == mtime:
        return _CACHE[1]

    prefs = default_display_prefs()
    if mtime is not None:
        try:
            prefs = parse_display_toml(target.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError):
            prefs = default_display_prefs()

    if use_cache:
        _CACHE = (mtime, prefs)
    return prefs


def clear_display_prefs_cache() -> None:
    global _CACHE
    _CACHE = None


def parse_display_toml(text: str) -> DisplayPrefs:
    """Parse our tiny TOML subset (sections + bool keys only)."""
    values = asdict(default_display_prefs())
    section = ""
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip().lower()
            continue
        match = _KEY.match(line)
        if not match:
            continue
        key = match.group(1).lower()
        raw_val = match.group(2).strip()
        if not _BOOL.match(raw_val):
            continue
        flag = raw_val.lower() == "true"
        if section == "show" and key in _SHOW_KEYS:
            values[key] = flag
        elif section == "extension" and key == "panel_badge":
            values["panel_badge"] = flag
    return DisplayPrefs(**values)


def reload_display(
    *,
    status_file: Path | None = None,
    push_bridge: bool = True,
) -> dict[str, Any]:
    """Clear prefs cache, refresh ``status.json`` display block, push bridge.

    Call after editing ``display.toml`` so the panel and VIEWE pick up changes
    without waiting for the next Cursor hook.
    """
    import json
    import urllib.error
    import urllib.request

    from cursor_agent_beacon.install import DEFAULT_STATUS_FILE
    from cursor_agent_beacon.models import AgentStatus

    clear_display_prefs_cache()
    config_path = ensure_display_config()
    prefs = load_display_prefs(use_cache=False)

    status_path = status_file or Path(
        os.environ.get(
            "CURSOR_AGENT_BEACON_STATUS_FILE",
            str(DEFAULT_STATUS_FILE),
        )
    )

    serial: str | None = None
    bridge_ok: bool | None = None
    bridge_error: str | None = None
    payload: dict[str, Any] | None = None

    if status_path.is_file():
        try:
            loaded = json.loads(status_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                payload = loaded
        except (OSError, json.JSONDecodeError, TypeError):
            payload = None

    if payload is not None:
        payload["display"] = prefs.to_dict()
        status_path.parent.mkdir(parents=True, exist_ok=True)
        status_path.write_text(
            json.dumps(payload, indent=2) + "\n",
            encoding="utf-8",
        )
        try:
            serial = AgentStatus.from_dict(payload).serial_line()
        except (KeyError, TypeError, ValueError):
            serial = None

        if push_bridge:
            url = (
                os.environ.get("CURSOR_AGENT_BEACON_HTTP_URL")
                or "http://127.0.0.1:8765/status"
            )
            try:
                body = json.dumps(payload).encode("utf-8")
                request = urllib.request.Request(
                    url,
                    data=body,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=2.0):
                    bridge_ok = True
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                bridge_ok = False
                bridge_error = str(exc)

    return {
        "config": str(config_path),
        "prefs": prefs.to_dict(),
        "status_file": str(status_path),
        "serial": serial,
        "bridge_ok": bridge_ok,
        "bridge_error": bridge_error,
    }
