"""One-shot end-user setup: hooks + optional GNOME panel."""

from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from cursor_agent_beacon.install import (
    DEFAULT_STATUS_FILE,
    install_gnome_extension,
    write_user_hooks,
)
from cursor_agent_beacon.paths import vendor_dir


@dataclass(frozen=True, slots=True)
class SetupResult:
    hooks_path: Path
    status_file: Path
    beacon_bin: Path
    gnome_path: Path | None = None


def resolve_beacon_bin(explicit: Path | str | None = None) -> Path:
    """Return the cursor-agent-beacon executable to embed in the hook wrapper."""
    if explicit is not None:
        path = Path(explicit).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"cursor-agent-beacon not found: {path}")
        return path

    argv0 = Path(sys.argv[0]).resolve()
    if argv0.name == "cursor-agent-beacon" and argv0.is_file():
        return argv0

    found = shutil.which("cursor-agent-beacon")
    if found:
        return Path(found).resolve()

    raise RuntimeError(
        "Could not locate cursor-agent-beacon. "
        'Install with: pip install "cursor-agent-beacon[bridge]" '
        "or run ./setup.sh from the repository root."
    )


def gnome_extension_available() -> bool:
    """True when GNOME extension assets and compile tool are present."""
    if not shutil.which("glib-compile-schemas"):
        return False
    return (vendor_dir() / "gnome-extension").is_dir()


def run_setup(
    *,
    skip_gnome: bool = False,
    hooks_only: bool = False,
    beacon_bin: Path | str | None = None,
) -> SetupResult:
    """Install user hooks and optionally the GNOME status panel."""
    bin_path = resolve_beacon_bin(beacon_bin)
    hooks_path = write_user_hooks(beacon_bin=bin_path)

    gnome_path: Path | None = None
    if not skip_gnome and not hooks_only and gnome_extension_available():
        gnome_path = install_gnome_extension()

    return SetupResult(
        hooks_path=hooks_path,
        status_file=DEFAULT_STATUS_FILE,
        beacon_bin=bin_path,
        gnome_path=gnome_path,
    )


def format_next_steps(result: SetupResult) -> str:
    """Human-readable post-setup instructions."""
    lines = [
        "Setup complete.",
        "",
        "Next steps:",
        "  1. Restart Cursor (hooks load at startup)",
    ]
    if result.gnome_path is not None:
        lines.extend(
            [
                "  2. Reload GNOME Shell: Alt+F2 → r (X11) or log out/in (Wayland)",
            ]
        )
    lines.extend(
        [
            "",
            f"Hooks: {result.hooks_path}",
            f"Status: {result.status_file.parent}/",
        ]
    )
    if result.gnome_path is not None:
        lines.append(f"GNOME panel: {result.gnome_path}")
    elif not gnome_extension_available():
        lines.append(
            "GNOME panel: skipped (not on GNOME or glib-compile-schemas missing)"
        )
    lines.append("")
    lines.append("Verify: cursor-agent-beacon doctor")
    return "\n".join(lines)
