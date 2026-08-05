#!/usr/bin/env python3
"""Build Open Graph / social preview card (1200×630).

Usage:
  pip install Pillow
  python3 scripts/build_social_card.py
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont, ImageSequence
except ImportError:
    print("Pillow required: pip install Pillow", file=sys.stderr)
    raise SystemExit(1)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "images" / "social.png"
W, H = 1200, 630


def font(size: int) -> ImageFont.ImageFont:
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        p = Path(path)
        if p.exists() and ("Bold" in path) == (size >= 48):
            return ImageFont.truetype(str(p), size)
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def main() -> None:
    card = Image.new("RGB", (W, H), (15, 17, 23))
    draw = ImageDraw.Draw(card)
    for y in range(H):
        t = y / H
        draw.line(
            [(0, y), (W, y)],
            fill=(int(15 + 8 * t), int(17 + 10 * t), int(23 + 20 * t)),
        )

    cx, cy = 900, 315
    for r, color, width in (
        (180, (42, 49, 72), 4),
        (130, (56, 189, 248), 6),
        (80, (125, 211, 252), 4),
    ):
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=width)

    robot = Image.open(ROOT / "themes/standard/assets/thinking.gif")
    frames = [f.convert("RGBA") for f in ImageSequence.Iterator(robot)]
    mid = frames[min(1, len(frames) - 1)]
    base = Image.new("RGBA", mid.size, (7, 16, 32, 255))
    mid = Image.alpha_composite(base, mid).resize((280, 280), Image.Resampling.NEAREST)
    card.paste(mid.convert("RGB"), (cx - 140, cy - 140))

    logo = Image.open(ROOT / "docs/images/logo.png").convert("RGBA").resize((96, 96))
    card.paste(logo, (72, 72), logo)

    draw.text((72, 200), "Cursor Agent Beacon", fill=(230, 233, 240), font=font(54))
    draw.text(
        (72, 280),
        "See what your Cursor agent is doing",
        fill=(125, 211, 252),
        font=font(28),
    )
    draw.text(
        (72, 320), "without watching the chat.", fill=(125, 211, 252), font=font(28)
    )
    draw.text(
        (72, 400),
        "GNOME panel  ·  status CLI  ·  optional desk display",
        fill=(139, 147, 167),
        font=font(22),
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    card.save(OUT, "PNG", optimize=True)
    print(f"Wrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
