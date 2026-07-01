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
DEFAULT_WRAPPER_PATH = Path.home() / ".cursor/hooks/cursor-agent-beacon.sh"


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
    beacon_bin: Path | str | None = None,
) -> Path:
    """Install merge-safe user hooks. Returns path to hooks.json."""
    cursor_dir = cursor_dir or Path.home() / ".cursor"
    status_file = status_file or DEFAULT_STATUS_FILE
    hooks_dir = cursor_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    status_file.parent.mkdir(parents=True, exist_ok=True)

    wrapper = hooks_dir / "cursor-agent-beacon.sh"
    if beacon_bin is not None:
        exec_line = f'"{Path(beacon_bin).resolve()}" run'
    else:
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
                'Install with: pip install "cursor-agent-beacon[bridge]" '
                'or pip install -e ".[dev,bridge]"'
            )


def strip_beacon_hooks_from_config(existing: dict[str, Any]) -> dict[str, Any]:
    """Return hooks.json with beacon hook entries removed."""
    merged: dict[str, Any] = dict(existing or {})
    hooks: dict[str, list[dict[str, Any]]] = dict(merged.get("hooks") or {})
    stripped_hooks: dict[str, list[dict[str, Any]]] = {}

    for hook_name, entries in hooks.items():
        kept = [item for item in entries if not _is_beacon_hook(item)]
        if kept:
            stripped_hooks[hook_name] = kept

    merged["hooks"] = stripped_hooks
    return merged


def remove_user_hooks(
    *,
    cursor_dir: Path | None = None,
) -> tuple[Path, bool]:
    """Remove beacon wrapper and hook entries. Returns (hooks.json path, changed)."""
    cursor_dir = cursor_dir or Path.home() / ".cursor"
    hooks_path = cursor_dir / "hooks.json"
    wrapper = cursor_dir / "hooks" / "cursor-agent-beacon.sh"
    changed = False

    if wrapper.is_file():
        try:
            content = wrapper.read_text(encoding="utf-8")
        except OSError:
            content = ""
        if BEACON_HOOK_MARKER in content or "cursor-agent-beacon" in content:
            wrapper.unlink(missing_ok=True)
            changed = True

    if not hooks_path.is_file():
        return hooks_path, changed

    try:
        existing = json.loads(hooks_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return hooks_path, changed

    stripped = strip_beacon_hooks_from_config(existing)
    if stripped.get("hooks") == existing.get("hooks"):
        return hooks_path, changed

    hooks_path.write_text(json.dumps(stripped, indent=2) + "\n", encoding="utf-8")
    return hooks_path, True


def remove_gnome_extension(
    *,
    dest_parent: Path | None = None,
) -> Path | None:
    """Disable and remove the installed GNOME extension. Returns path if removed."""
    dest_parent = dest_parent or (Path.home() / ".local/share/gnome-shell/extensions")
    dest = dest_parent / GNOME_UUID

    subprocess.run(
        ["gnome-extensions", "disable", GNOME_UUID],
        check=False,
        capture_output=True,
    )

    if not dest.exists():
        return None

    shutil.rmtree(dest)
    return dest


def remove_status_data(
    *,
    status_dir: Path | None = None,
) -> Path | None:
    """Delete user status directory. Returns path if removed."""
    status_dir = status_dir or DEFAULT_STATUS_DIR
    if not status_dir.exists():
        return None
    shutil.rmtree(status_dir)
    return status_dir


def uninstall_desktop(
    *,
    hooks_only: bool = False,
    skip_gnome: bool = False,
    keep_status: bool = True,
    cursor_dir: Path | None = None,
    status_dir: Path | None = None,
) -> dict[str, Path | None]:
    """Remove hooks, optional GNOME panel, and optional status data."""
    hooks_path, hooks_changed = remove_user_hooks(cursor_dir=cursor_dir)
    result: dict[str, Path | None] = {
        "hooks_path": hooks_path if hooks_changed else None,
        "gnome_path": None,
        "status_dir": None,
    }

    if not skip_gnome and not hooks_only:
        result["gnome_path"] = remove_gnome_extension()

    if not keep_status:
        result["status_dir"] = remove_status_data(status_dir=status_dir)

    return result
