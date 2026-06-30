"""Resolve packaged and development asset paths."""

from __future__ import annotations

import os
import sys
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def package_root() -> Path:
    """Installed package directory (wheel or editable)."""
    import cursor_agent_beacon

    return Path(cursor_agent_beacon.__file__).resolve().parent


def default_themes_dir() -> Path:
    """Themes root: env override → packaged → repo checkout."""
    env_root = os.environ.get("CURSOR_AGENT_BEACON_THEMES_DIR")
    if env_root:
        return Path(env_root)

    packaged = package_root() / "themes"
    if packaged.is_dir():
        return packaged

    # ponytail: dev checkout with themes/ at repo root
    repo_root = package_root().parents[1]
    checkout = repo_root / "themes"
    if checkout.is_dir():
        return checkout

    return Path("themes")


def vendor_dir() -> Path:
    """Bundled install assets (hooks template, GNOME extension)."""
    packaged = package_root() / "vendor"
    if packaged.is_dir():
        return packaged

    repo_root = package_root().parents[1]
    if (repo_root / "gnome-extension").is_dir():
        return repo_root
    return packaged


def beacon_command() -> list[str]:
    """Argv prefix to invoke the hook handler."""
    override = os.environ.get("CURSOR_AGENT_BEACON_PYTHON")
    if override:
        return [override, "-m", "cursor_agent_beacon.cli", "run"]

    exe = Path(sys.executable)
    scripts = exe.parent / "cursor-agent-beacon"
    if scripts.is_file():
        return [str(scripts), "run"]
    return [str(exe), "-m", "cursor_agent_beacon.cli", "run"]
