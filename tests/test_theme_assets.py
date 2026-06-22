"""Validate bundled theme packs and manifest integrity."""

from __future__ import annotations

from pathlib import Path

import pytest

from cursor_agent_beacon.theme import load_theme

REPO_ROOT = Path(__file__).resolve().parents[1]
THEMES_ROOT = REPO_ROOT / "themes"


def test_standard_theme_manifest_matches_assets():
    theme = load_theme("standard", THEMES_ROOT)
    assert theme.theme_id == "standard"
    assert theme.animations, "standard theme must define at least one state animation"

    for state, animation in theme.animations.items():
        assert animation.path.is_file(), (
            f"Missing GIF for state '{state}': {animation.path}"
        )
        assert animation.path.suffix.lower() == ".gif"
        assert animation.caption


def test_standard_theme_covers_core_agent_states():
    theme = load_theme("standard", THEMES_ROOT)
    required = {
        "idle",
        "waiting",
        "thinking",
        "running_shell",
        "running_mcp",
        "success",
        "error",
    }
    missing = required - set(theme.animations)
    assert not missing, f"standard theme missing states: {sorted(missing)}"


@pytest.mark.parametrize("theme_id", ["standard"])
def test_theme_manifest_display_metadata(theme_id: str):
    theme = load_theme(theme_id, THEMES_ROOT)
    display = theme.manifest.get("display") or {}
    assert display.get("width") == 240
    assert display.get("height") == 240
    assert display.get("format") == "gif"
