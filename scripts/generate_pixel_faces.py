#!/usr/bin/env python3
"""Export pixel face frames from pixel-faces.json to PNG sprite sheets."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Pillow required: pip install Pillow", file=sys.stderr)
    raise SystemExit(1)


def load_faces(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def grid_to_image(grid: list[str], palette: dict[str, str | None], scale: int) -> Image.Image:
    height = len(grid)
    width = max(len(row) for row in grid)
    img = Image.new("RGBA", (width * scale, height * scale), (0, 0, 0, 0))

    for y, row in enumerate(grid):
        for x, ch in enumerate(row):
            color = palette.get(ch)
            if not color or color == "transparent":
                continue
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
            block = Image.new("RGBA", (scale, scale), (r, g, b, 255))
            img.paste(block, (x * scale, y * scale))

    return img


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate PNGs from pixel face definitions")
    parser.add_argument(
        "--faces",
        type=Path,
        default=Path("themes/standard/pixel-faces.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("themes/standard/assets/faces"),
    )
    parser.add_argument("--scale", type=int, default=10, help="Pixels per grid cell")
    args = parser.parse_args()

    data = load_faces(args.faces)
    palette = data["palette"]
    args.output.mkdir(parents=True, exist_ok=True)

    for face_id, face in data["faces"].items():
        frames = face.get("frames", [])
        for index, raw in enumerate(frames):
            if isinstance(raw, str):
                grid = raw.split("\n")
            elif isinstance(raw, list):
                grid = raw
            else:
                continue
            suffix = f"_{index:02d}" if len(frames) > 1 else ""
            out_path = args.output / f"{face_id}{suffix}.png"
            image = grid_to_image(grid, palette, args.scale)
            image.save(out_path)
            print(f"  {out_path}")

    print(f"\nExported {sum(len(f.get('frames', [])) for f in data['faces'].values())} PNG frames.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
