#!/usr/bin/env python3
"""Default desk face: expressive eyes, 480×480.

Flat fills (white, one gray, one green) on the panel background. Encoded with
Pillow's fixed palette. gifski's temporal dither is for photos; it grains this
art and blows the flash budget.

Reference expressions used: feliz, risa, risa de ojos, seguro, oops, shock.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
DISPLAY_SIZE = 480
SS = 2
BG = (7, 16, 32)
WHITE = (255, 255, 255, 255)
SMILE = (186, 196, 208, 255)
GREEN = (190, 240, 70, 255)


def _mix(
    a: tuple[int, int, int], b: tuple[int, int, int], t: float
) -> tuple[int, int, int]:
    return tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))


def _palette_image() -> Image.Image:
    colors = [
        BG,
        (255, 255, 255),
        SMILE[:3],
        GREEN[:3],
        _mix(BG, (255, 255, 255), 0.28),
        _mix(BG, (255, 255, 255), 0.55),
        _mix(BG, (255, 255, 255), 0.82),
        _mix(BG, GREEN[:3], 0.45),
        _mix(BG, SMILE[:3], 0.5),
    ]
    pal = Image.new("P", (1, 1))
    flat: list[int] = []
    for color in colors:
        flat.extend(color)
    flat.extend([0] * (768 - len(flat)))
    pal.putpalette(flat)
    return pal


PALETTE_IMG = _palette_image()


def _s(n: float) -> int:
    return int(round(n * SS))


def _canvas() -> Image.Image:
    return Image.new("RGBA", (DISPLAY_SIZE * SS, DISPLAY_SIZE * SS), (*BG, 255))


def _paste(
    base: Image.Image, layer: Image.Image, cx: int, cy: int, angle: float
) -> None:
    if angle:
        layer = layer.rotate(angle, resample=Image.Resampling.BICUBIC)
    w, h = layer.size
    base.paste(layer, (cx - w // 2, cy - h // 2), layer)


def _erase(layer: Image.Image, mask: Image.Image) -> Image.Image:
    r, g, b, a = layer.split()
    return Image.merge("RGBA", (r, g, b, ImageChops.subtract(a, mask)))


def _eye(
    base: Image.Image,
    cx: float,
    cy: float,
    rw: float,
    rh: float,
    angle: float = 0,
    lid: float = 0,
) -> None:
    # A full lid erase disappears on the panel. Closed pose is the smile arc.
    if lid >= 0.72:
        _crescent(base, cx, cy + rh * 0.2, rw, min(rh, 42), 16, angle)
        return
    cx, cy, rw, rh = _s(cx), _s(cy), _s(rw), _s(rh)
    w, h = rw * 2, rh * 2
    pad = max(w, h)
    layer = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.ellipse([pad, pad, pad + w, pad + h], fill=WHITE)
    if lid > 0:
        mask = Image.new("L", layer.size, 0)
        md = ImageDraw.Draw(mask)
        cut = int(h * min(lid, 0.96))
        bulge = max(4, rh // 4)
        md.rectangle([pad - 8, 0, pad + w + 8, pad + cut], fill=255)
        md.ellipse(
            [pad - 4, pad + cut - bulge, pad + w + 4, pad + cut + bulge],
            fill=255,
        )
        layer = _erase(layer, mask)
    _paste(base, layer, cx, cy, angle)


def _crescent(
    base: Image.Image,
    cx: float,
    cy: float,
    rw: float,
    rh: float,
    thick: float,
    angle: float = 0,
) -> None:
    """Top cap of an oval: a closed smile eye."""
    cx, cy, rw, rh, thick = _s(cx), _s(cy), _s(rw), _s(rh), _s(thick)
    w, h = rw * 2, rh * 2
    pad = max(w, h)
    layer = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.ellipse([pad, pad, pad + w, pad + h], fill=WHITE)
    mask = Image.new("L", layer.size, 0)
    shift = max(1, thick)
    ImageDraw.Draw(mask).ellipse(
        [pad, pad + shift, pad + w, pad + h + shift],
        fill=255,
    )
    _paste(base, _erase(layer, mask), cx, cy, angle)


def _feliz(
    base: Image.Image,
    *,
    dx: float = 0,
    dy: float = 0,
    lid: float = 0,
    rw: float = 54,
    rh: float = 76,
    tilt: float = 13,
    spread: float = 90,
    cy: float = 228,
) -> None:
    _eye(base, 240 - spread + dx, cy + dy, rw, rh, tilt, lid)
    _eye(base, 240 + spread + dx, cy + dy, rw, rh, -tilt, lid)


def _risa(
    base: Image.Image,
    *,
    thick: float = 18,
    mouth: float = 0,
) -> None:
    _crescent(base, 150, 220, 64, 42, thick, 16)
    _crescent(base, 330, 220, 64, 42, thick, -16)
    if mouth:
        d = ImageDraw.Draw(base)
        cx, cy, rw, rh = _s(240), _s(318), _s(mouth), _s(26)
        d.arc(
            [cx - rw, cy - rh, cx + rw, cy + rh],
            18,
            162,
            fill=SMILE,
            width=_s(8),
        )


def _ticks(base: Image.Image, reach: float) -> None:
    if reach <= 0:
        return
    d = ImageDraw.Draw(base)
    w = _s(5)

    def mark(cx: float, cy: float) -> None:
        x, y, r = _s(cx), _s(cy), _s(reach)
        d.line([(x - r, y), (x - r // 3, y - r)], fill=GREEN, width=w)
        d.line([(x + r // 3, y), (x + r, y - r)], fill=GREEN, width=w)

    mark(150, 150)
    mark(330, 150)


def _drop(base: Image.Image, cx: float, cy: float, s: float = 11) -> None:
    x, y, s = _s(cx), _s(cy), _s(s)
    d = ImageDraw.Draw(base)
    d.polygon([(x, y - int(s * 1.7)), (x - s, y), (x + s, y)], fill=GREEN)
    d.ellipse([x - s, y - s // 3, x + s, y + int(s * 1.5)], fill=GREEN)


def _spark(base: Image.Image, kind: str, x: float, y: float, r: float = 11) -> None:
    d = ImageDraw.Draw(base)
    px, py, pr = _s(x), _s(y), _s(r)
    if kind == "dot":
        d.ellipse([px - pr // 2, py - pr // 2, px + pr // 2, py + pr // 2], fill=GREEN)
        return
    w = _s(4)
    d.line([(px - pr, py), (px + pr, py)], fill=GREEN, width=w)
    d.line([(px, py - pr), (px, py + pr)], fill=GREEN, width=w)


def _finish(img: Image.Image) -> Image.Image:
    rgb = Image.new("RGB", img.size, BG)
    rgb.paste(img, mask=img.split()[-1])
    rgb = rgb.resize((DISPLAY_SIZE, DISPLAY_SIZE), Image.Resampling.LANCZOS)
    return rgb.quantize(palette=PALETTE_IMG, dither=Image.Dither.NONE)


def _nudge(img: Image.Image, dx: float) -> Image.Image:
    out = _canvas()
    out.paste(img, (_s(dx), 0))
    return out


def _frames(draw_frames: list[Callable[[Image.Image], None]]) -> list[Image.Image]:
    rendered: list[Image.Image] = []
    for draw in draw_frames:
        img = _canvas()
        draw(img)
        rendered.append(_finish(img))
    return rendered


def build_faces() -> dict:
    def sleeping_at(i: int) -> Callable[[Image.Image], None]:
        lid = (0.08, 0.42, 0.86, 0.42)[i]
        dy = (0, 8, 14, 8)[i]

        def draw(img: Image.Image) -> None:
            _feliz(img, dy=dy, lid=lid, rh=70)

        return draw

    def waiting_at(i: int) -> Callable[[Image.Image], None]:
        dx = (0, 16, 0, -10)[i]
        lid = (0, 0, 0.9, 0)[i]

        def draw(img: Image.Image) -> None:
            _feliz(img, dx=dx, lid=lid)

        return draw

    def thinking_at(i: int) -> Callable[[Image.Image], None]:
        dx = (-20, -6, 18, 0)[i]
        dy = (-28, -20, -24, 0)[i]
        lid = (0, 0, 0, 0.88)[i]

        def draw(img: Image.Image) -> None:
            _feliz(img, dx=dx, dy=dy, lid=lid, rw=50, rh=68, tilt=8)

        return draw

    def shell_at(i: int) -> Callable[[Image.Image], None]:
        dx = (-30, -8, 30, 8)[i]

        def draw(img: Image.Image) -> None:
            _feliz(img, dx=dx, rw=52, rh=34, tilt=6, spread=86)

        return draw

    sparks = (
        (("plus", 52, 150), ("dot", 432, 140), ("plus", 240, 96)),
        (("dot", 64, 118), ("plus", 428, 168), ("dot", 240, 88)),
        (("plus", 46, 186), ("dot", 438, 118), ("plus", 188, 92)),
        (("dot", 72, 136), ("plus", 422, 148), ("dot", 292, 92)),
    )

    def mcp_at(i: int) -> Callable[[Image.Image], None]:
        marks = sparks[i]

        def draw(img: Image.Image) -> None:
            _feliz(img, rw=62, rh=62, tilt=0, spread=94)
            for kind, x, y in marks:
                _spark(img, kind, x, y)

        return draw

    def success_at(i: int) -> Callable[[Image.Image], None]:
        thick = (16, 24, 16, 24)[i]
        mouth = (34, 48, 34, 48)[i]

        def draw(img: Image.Image) -> None:
            _risa(img, thick=thick, mouth=mouth)

        return draw

    def shock(img: Image.Image) -> None:
        _feliz(img, rw=40, rh=40, tilt=0, spread=78, cy=232)

    def oops(sweat: bool) -> Callable[[Image.Image], None]:
        def draw(img: Image.Image) -> None:
            _eye(img, 146, 214, 58, 80, 12, 0)
            _eye(img, 322, 238, 42, 58, -6, 0)
            if sweat:
                _drop(img, 378, 156)

        return draw

    def stop_at(i: int) -> Callable[[Image.Image], None]:
        reach = (0, 12, 18, 12)[i]

        def draw(img: Image.Image) -> None:
            _risa(img, thick=20, mouth=0)
            _ticks(img, reach)

        return draw

    error_draws: list[Callable[[Image.Image], None]] = []
    for dx in (-16, 16, -16):

        def shaken(img: Image.Image, dx: float = dx) -> None:
            tmp = _canvas()
            shock(tmp)
            nudged = _nudge(tmp, dx)
            img.paste(nudged)

        error_draws.append(shaken)
    error_draws.extend([oops(True), oops(False), oops(True)])

    meta = {
        "sleeping": ("Sleeping", "Idle — eyes drift shut"),
        "waiting": ("Waiting", "Happy eyes, glance, blink"),
        "thinking": ("Thinking", "Eyes look up and around"),
        "running_shell": ("Running shell", "Narrow eyes scanning"),
        "running_mcp": ("MCP tool", "Steady eyes, green spark"),
        "success": ("Success", "Smile that pulses"),
        "error": ("Error", "Shock, then a sweat drop"),
        "stop": ("Session done", "Laughing eyes"),
    }
    built: dict = {}
    groups: list[tuple[str, list[Callable[[Image.Image], None]]]] = [
        ("sleeping", [sleeping_at(i) for i in range(4)]),
        ("waiting", [waiting_at(i) for i in range(4)]),
        ("thinking", [thinking_at(i) for i in range(4)]),
        ("running_shell", [shell_at(i) for i in range(4)]),
        ("running_mcp", [mcp_at(i) for i in range(4)]),
        ("success", [success_at(i) for i in range(4)]),
        ("error", error_draws),
        ("stop", [stop_at(i) for i in range(4)]),
    ]
    for key, draws in groups:
        label, caption = meta[key]
        built[key] = {
            "label": label,
            "caption": caption,
            "frames": _frames(draws),
        }
    return built


def frame_durations(sprite_key: str, frame_count: int) -> list[int]:
    if sprite_key == "sleeping":
        return [700] * frame_count
    if sprite_key == "error" and frame_count >= 6:
        return [120, 120, 120, 500, 500, 500]
    if sprite_key == "success":
        return [350] * frame_count
    if sprite_key == "running_shell":
        return [160] * frame_count
    return [280] * frame_count


def state_map() -> dict[str, str]:
    return {
        "idle": "sleeping",
        "waiting": "waiting",
        "thinking": "thinking",
        "running_shell": "running_shell",
        "running_mcp": "running_mcp",
        "success": "success",
        "error": "error",
        "stop": "stop",
    }


def write_preview_bundle(faces: dict) -> Path:
    path = ROOT / "preview" / "beacon-sprites.js"
    bundle = {
        key: {"label": face["label"], "caption": face["caption"]}
        for key, face in faces.items()
    }
    js = (
        "/** Auto-generated by scripts/build_character_sprites.py — do not edit. */\n"
        "window.BEACON_SPRITES = " + json.dumps({"faces": bundle}, indent=2) + ";\n"
    )
    path.write_text(js, encoding="utf-8")
    return path


def main() -> int:
    faces = build_faces()
    print(f"Wrote {write_preview_bundle(faces)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
