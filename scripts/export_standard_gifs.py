#!/usr/bin/env python3
"""Export standard theme GIFs from pixel sprite definitions."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from PIL import Image
except ImportError:
    print("Pillow required: pip install Pillow", file=sys.stderr)
    raise SystemExit(1)

from build_character_sprites import (
    BG_HEX,
    GRID,
    PALETTE,
    build_faces,
    frame_durations,
    state_map,
    write_pixel_faces,
    write_preview_bundle,
)

ROOT = Path(__file__).resolve().parents[1]


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def parse_grid(raw: str) -> list[str]:
    return raw.split("\n")


def grid_to_image(grid: list[str], scale: int) -> Image.Image:
    bg = hex_to_rgb(BG_HEX)
    img = Image.new("RGB", (GRID * scale, GRID * scale), bg)
    pixel = img.load()
    assert pixel is not None

    for y, row in enumerate(grid):
        for x, ch in enumerate(row):
            color = PALETTE.get(ch)
            if not color:
                continue
            rgb = hex_to_rgb(color)
            for dy in range(scale):
                for dx in range(scale):
                    pixel[x * scale + dx, y * scale + dy] = rgb
    return img


def export_gif(frames: list[str], dest: Path, sprite_key: str) -> None:
    grids = [parse_grid(frame) for frame in frames]
    images = [grid_to_image(grid, scale=10) for grid in grids]
    durations = frame_durations(sprite_key, len(images))
    images[0].save(
        dest,
        save_all=True,
        append_images=images[1:],
        duration=durations,
        loop=0,
        disposal=2,
    )


def write_manifest(assets_dir: Path) -> Path:
    manifest_path = ROOT / "themes" / "standard" / "manifest.json"
    states_cfg: dict = {}
    for agent_state, sprite_key in state_map().items():
        gif_name = f"{sprite_key}.gif"
        states_cfg[agent_state] = {
            "animation": f"assets/{gif_name}",
            "loop": agent_state != "stop",
            "caption": sprite_key.replace("_", " ").title(),
        }

    manifest = {
        "id": "standard",
        "name": "Beacon Bot",
        "description": "Default pixel robot GIFs bundled with the repository",
        "license": "MIT",
        "author": "cursor-agent-beacon",
        "display": {
            "width": 240,
            "height": 240,
            "format": "gif",
            "background": BG_HEX,
        },
        "display_mode": "gif",
        "pixel_faces": "pixel-faces.json",
        "states": states_cfg,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Export standard theme GIF assets")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "themes" / "standard" / "assets",
    )
    args = parser.parse_args()

    faces = build_faces()
    write_pixel_faces(faces)
    write_preview_bundle(faces)

    args.output.mkdir(parents=True, exist_ok=True)
    for sprite_key, face in faces.items():
        dest = args.output / f"{sprite_key}.gif"
        export_gif(face["frames"], dest, sprite_key)
        print(f"  {dest}")

    manifest = write_manifest(args.output)
    print(f"Wrote {manifest}")
    print(f"\nExported {len(faces)} GIFs to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
