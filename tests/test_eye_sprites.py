"""Default eye theme: every state animates and keeps a visible eye."""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_character_sprites import build_faces, state_map  # noqa: E402

BG = (7, 16, 32)


def _counts(frame: Image.Image) -> tuple[int, int]:
    rgb = frame.convert("RGB")
    white = green = 0
    step = 2
    for y in range(0, rgb.height, step):
        for x in range(0, rgb.width, step):
            r, g, b = rgb.getpixel((x, y))
            if r > 230 and g > 230 and b > 230:
                white += 1
            elif g > 160 and g > r + 30 and g > b:
                green += 1
    return white, green


def test_each_state_animates_and_keeps_eyes():
    faces = build_faces()
    assert set(state_map().values()) == set(faces)
    for key, face in faces.items():
        frames = face["frames"]
        assert len(frames) >= 4, key
        first = frames[0].convert("RGB")
        assert first.size == (480, 480)
        assert first.getpixel((0, 0)) == BG
        assert first.tobytes() != frames[1].convert("RGB").tobytes()
        for frame in frames:
            white, _green = _counts(frame)
            assert white > 40, key

    _white, mcp_green = _counts(faces["running_mcp"]["frames"][0])
    shock_white, shock_green = _counts(faces["error"]["frames"][0])
    oops_white, oops_green = _counts(faces["error"]["frames"][3])
    assert mcp_green > 0
    assert shock_green == 0
    assert oops_green > 0
    assert oops_white > shock_white
