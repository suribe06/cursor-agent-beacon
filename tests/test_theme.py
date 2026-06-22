"""Tests for theme pack loading."""

import json
from pathlib import Path

import pytest

from cursor_agent_beacon.theme import load_theme


def test_load_standard_theme(tmp_path: Path):
    theme_root = tmp_path / "standard"
    assets = theme_root / "assets"
    assets.mkdir(parents=True)
    (assets / "sleeping.gif").write_bytes(b"GIF")

    manifest = {
        "id": "standard",
        "name": "Test",
        "states": {
            "idle": {
                "animation": "assets/sleeping.gif",
                "loop": True,
                "caption": "Sleeping",
            }
        },
    }
    (theme_root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    theme = load_theme("standard", themes_root=tmp_path)
    anim = theme.animation_for("idle")
    assert anim is not None
    assert anim.path.name == "sleeping.gif"
    assert anim.loop is True
