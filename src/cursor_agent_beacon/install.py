"""Install user-level Cursor hooks and GNOME extension assets."""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
from pathlib import Path
from typing import Any

from cursor_agent_beacon.hooks import SUPPORTED_HOOKS
from cursor_agent_beacon.paths import beacon_command, vendor_dir

BEACON_HOOK_MARKER = "cursor-agent-beacon"
GNOME_UUID = "cursor-status-panel@suribe06"
DEFAULT_STATUS_DIR = Path.home() / ".local/share/cursor-agent-beacon"
DEFAULT_STATUS_FILE = DEFAULT_STATUS_DIR / "status.json"


def _hooks_json_entry(command: str) -> dict[str, Any]:
    return {"command": command, "timeout": 5}


def _is_beacon_hook(entry: dict[str, Any]) -> bool:
    cmd = str(entry.get("command") or "")
    return BEACON_HOOK_MARKER in cmd


def merge_hooks_config(
    existing: dict[str, Any] | None,
    hook_command: str,
) -> dict[str, Any]:
    """Merge beacon hooks into an existing hooks.json without dropping other hooks."""
    merged: dict[str, Any] = dict(existing or {})
    merged.setdefault("version", 1)
    hooks: dict[str, list[dict[str, Any]]] = dict(merged.get("hooks") or {})

    beacon_entry = _hooks_json_entry(hook_command)
    for hook_name in SUPPORTED_HOOKS:
        existing_entries = hooks.get(hook_name, [])
        current = [item for item in existing_entries if not _is_beacon_hook(item)]
        hooks[hook_name] = [beacon_entry, *current]

    merged["hooks"] = hooks
    return merged


def write_user_hooks(
    *,
    cursor_dir: Path | None = None,
    status_file: Path | None = None,
) -> Path:
    """Install merge-safe user hooks. Returns path to hooks.json."""
    cursor_dir = cursor_dir or Path.home() / ".cursor"
    status_file = status_file or DEFAULT_STATUS_FILE
    hooks_dir = cursor_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    status_file.parent.mkdir(parents=True, exist_ok=True)

    wrapper = hooks_dir / "cursor-agent-beacon.sh"
    cmd_parts = beacon_command()
    exec_line = " ".join(_shell_quote(part) for part in cmd_parts)
    wrapper.write_text(
        "#!/usr/bin/env bash\n"
        f'export CURSOR_AGENT_BEACON_STATUS_FILE="{status_file}"\n'
        f"exec {exec_line}\n",
        encoding="utf-8",
    )
    wrapper.chmod(wrapper.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    hooks_path = cursor_dir / "hooks.json"
    existing: dict[str, Any] | None = None
    if hooks_path.is_file():
        try:
            existing = json.loads(hooks_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = None

    hook_command = "./hooks/cursor-agent-beacon.sh"
    merged = merge_hooks_config(existing, hook_command)
    hooks_path.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
    return hooks_path


def install_gnome_extension(
    *,
    dest_parent: Path | None = None,
) -> Path:
    """Copy GNOME extension into ~/.local/share/gnome-shell/extensions/."""
    src = vendor_dir() / "gnome-extension"
    if not src.is_dir():
        raise FileNotFoundError(f"GNOME extension not found: {src}")

    dest_parent = dest_parent or (Path.home() / ".local/share/gnome-shell/extensions")
    dest = dest_parent / GNOME_UUID
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)

    schemas = dest / "schemas"
    if schemas.is_dir():
        subprocess.run(
            ["glib-compile-schemas", str(schemas)],
            check=False,
            capture_output=True,
        )

    for cmd in (
        ["gnome-extensions", "disable", GNOME_UUID],
        ["gnome-extensions", "enable", GNOME_UUID],
    ):
        subprocess.run(cmd, check=False, capture_output=True)

    return dest


def install_desktop() -> tuple[Path, Path]:
    """Install user hooks + GNOME panel. Returns (hooks.json, extension dir)."""
    hooks_path = write_user_hooks()
    ext_path = install_gnome_extension()
    return hooks_path, ext_path


def _shell_quote(value: str) -> str:
    if not value:
        return "''"
    if all(ch.isalnum() or ch in "/._-" for ch in value):
        return value
    return "'" + value.replace("'", "'\\''") + "'"


def verify_package_installed() -> None:
    """Raise if cursor_agent_beacon is not importable in the active environment."""
    import cursor_agent_beacon  # noqa: F401

    if not os.environ.get("CURSOR_AGENT_BEACON_SKIP_VERIFY"):
        cmd = beacon_command()
        if cmd[0].endswith("cursor-agent-beacon") and not Path(cmd[0]).is_file():
            raise RuntimeError(
                "cursor-agent-beacon CLI not found. "
                'Install with: pip install -e ".[dev,bridge]"'
            )
