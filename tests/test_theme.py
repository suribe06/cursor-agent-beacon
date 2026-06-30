"""Tests for theme pack loading."""

import json
from pathlib import Path

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


def test_stop_hook_uses_stop_animation(tmp_path: Path):
    theme_root = tmp_path / "standard"
    assets = theme_root / "assets"
    assets.mkdir(parents=True)
    (assets / "success.gif").write_bytes(b"GIF")
    (assets / "stop.gif").write_bytes(b"GIF2")

    manifest = {
        "id": "standard",
        "name": "Test",
        "states": {
            "success": {"animation": "assets/success.gif", "loop": True},
            "stop": {"animation": "assets/stop.gif", "loop": False},
        },
    }
    (theme_root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    theme = load_theme("standard", themes_root=tmp_path)
    anim = theme.animation_for("success", hook_event_name="stop")
    assert anim is not None
    assert anim.path.name == "stop.gif"
