"""Photo reference + custom character GIF pack."""

import json
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from pack_character_theme import main as pack_main  # noqa: E402
from pixelate_reference import main as pixelate_main  # noqa: E402

from cursor_agent_beacon.theme import load_theme  # noqa: E402


def test_pixelate_reference_writes_palette(tmp_path: Path, monkeypatch):
    photo = tmp_path / "photo.png"
    im = Image.new("RGB", (32, 32), (10, 20, 30))
    for y in range(8, 24):
        for x in range(8, 24):
            im.putpixel((x, y), (220, 40, 40))
    im.save(photo)
    out = tmp_path / "src"
    monkeypatch.setattr(
        "sys.argv",
        [
            "pixelate_reference.py",
            str(photo),
            "--out",
            str(out),
            "--size",
            "8",
            "--colors",
            "4",
        ],
    )
    assert pixelate_main() == 0
    ref = Image.open(out / "ref.png")
    assert ref.size == (8, 8)
    palette = json.loads((out / "palette.json").read_text(encoding="utf-8"))
    assert palette["background"] == "#0a141e"
    assert "#dc2828" in palette["colors"]


def test_pack_character_theme_scales_and_falls_back(tmp_path: Path, monkeypatch):
    frames = tmp_path / "frames"
    frames.mkdir()
    Image.new("RGBA", (4, 4), (10, 20, 30, 255)).save(frames / "idle-000.png")
    Image.new("RGBA", (4, 4), (10, 20, 80, 255)).save(frames / "idle-001.png")
    Image.new("RGBA", (4, 4), (200, 180, 40, 255)).save(frames / "thinking-000.png")
    themes = tmp_path / "themes"
    monkeypatch.setattr(
        "sys.argv",
        [
            "pack_character_theme.py",
            str(frames),
            "--id",
            "fox",
            "--name",
            "Fox",
            "--themes-root",
            str(themes),
        ],
    )
    assert pack_main() == 0
    gif = Image.open(themes / "custom" / "fox" / "assets" / "idle.gif")
    assert gif.size == (480, 480)
    assert gif.n_frames == 2
    theme = load_theme("fox", themes_root=themes)
    assert theme.animation_for("thinking") is not None
    assert theme.animation_for("error").path.name == "error.gif"
    assert (themes / "custom" / "fox" / "assets" / "error.gif").is_file()
