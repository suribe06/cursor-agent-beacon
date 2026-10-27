#!/usr/bin/env python3
"""Photo → small pixel reference + palette. Not the art that goes on the screen."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    raise SystemExit("Pillow required: pip install Pillow")


def hex_of(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def square_crop(im: Image.Image) -> Image.Image:
    w, h = im.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    return im.crop((left, top, left + side, top + side))


def pixelate(src: Path, size: int, colors: int) -> tuple[Image.Image, str, list[str]]:
    im = square_crop(Image.open(src).convert("RGB"))
    small = im.resize((size, size), Image.Resampling.BOX)
    small = small.quantize(
        colors=colors,
        method=Image.Quantize.MEDIANCUT,
        dither=Image.Dither.NONE,
    )
    small = small.convert("RGB")
    flat = getattr(small, "get_flattened_data", small.getdata)
    px = list(flat())
    corners = [px[0], px[size - 1], px[-size], px[-1]]
    background = Counter(corners).most_common(1)[0][0]
    palette = []
    for color, _count in Counter(px).most_common():
        if color == background:
            continue
        palette.append(hex_of(color))
    return small, hex_of(background), palette


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("photo", type=Path)
    parser.add_argument("--out", type=Path, required=True, help="Output directory")
    parser.add_argument("--size", type=int, default=32)
    parser.add_argument("--colors", type=int, default=12)
    args = parser.parse_args()

    small, background, colors = pixelate(args.photo, args.size, args.colors)
    args.out.mkdir(parents=True, exist_ok=True)
    ref = args.out / "ref.png"
    small.save(ref)
    payload = {"size": args.size, "background": background, "colors": colors}
    text = json.dumps(payload, indent=2) + "\n"
    (args.out / "palette.json").write_text(text, encoding="utf-8")
    print(f"{ref}  bg={background}  colors={len(colors)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
