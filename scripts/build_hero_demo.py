#!/usr/bin/env python3
"""Build README hero demo GIF from standard theme state animations.

Usage:
  pip install Pillow
  python3 scripts/build_hero_demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    from PIL import Image, ImageSequence
except ImportError:
    print("Pillow required: pip install Pillow", file=sys.stderr)
    raise SystemExit(1)

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "themes" / "standard" / "assets"
OUT = ROOT / "docs" / "images" / "hero-demo.gif"

# State GIFs and how many full loops each plays in the demo.
SEQUENCE: list[tuple[str, int]] = [
    ("thinking.gif", 3),
    ("running_shell.gif", 3),
    ("success.gif", 3),
]
SIZE = (320, 320)
BG = (7, 16, 32, 255)


def load_loops(name: str, loops: int) -> tuple[list[Image.Image], list[int]]:
    im = Image.open(ASSETS / name)
    frames: list[Image.Image] = []
    durations: list[int] = []
    for frame in ImageSequence.Iterator(im):
        rgba = frame.convert("RGBA")
        base = Image.new("RGBA", rgba.size, BG)
        composed = Image.alpha_composite(base, rgba).convert("RGB")
        frames.append(composed.resize(SIZE, Image.Resampling.NEAREST))
        durations.append(int(frame.info.get("duration", 120) or 120))
    out_f: list[Image.Image] = []
    out_d: list[int] = []
    for _ in range(loops):
        out_f.extend(frames)
        out_d.extend(durations)
    return out_f, out_d


def main() -> None:
    all_frames: list[Image.Image] = []
    all_durations: list[int] = []
    for name, loops in SEQUENCE:
        frames, durations = load_loops(name, loops)
        all_frames.extend(frames)
        all_durations.extend(durations)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    all_frames[0].save(
        OUT,
        save_all=True,
        append_images=all_frames[1:],
        duration=all_durations,
        loop=0,
        optimize=False,
        disposal=2,
    )
    print(f"Wrote {OUT} ({len(all_frames)} frames, {OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
