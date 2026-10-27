#!/usr/bin/env python3
"""Pack <state>-NNN.png frames into themes/custom/<id>."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    raise SystemExit("Pillow required: pip install Pillow")

ROOT = Path(__file__).resolve().parents[1]
STATES = (
    "idle",
    "waiting",
    "thinking",
    "running_shell",
    "running_mcp",
    "success",
    "error",
    "stop",
)
CANVAS = 480
FRAME_MS = 160


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def fit(im: Image.Image, bg: tuple[int, int, int]) -> Image.Image:
    im = im.convert("RGBA")
    if im.width <= CANVAS and im.height <= CANVAS:
        scale = max(1, min(CANVAS // im.width, CANVAS // im.height))
        w, h = im.width * scale, im.height * scale
    else:
        scale = min(CANVAS / im.width, CANVAS / im.height)
        w, h = max(1, int(im.width * scale)), max(1, int(im.height * scale))
    resized = im.resize((w, h), Image.Resampling.NEAREST)
    canvas = Image.new("RGB", (CANVAS, CANVAS), bg)
    canvas.paste(resized, ((CANVAS - w) // 2, (CANVAS - h) // 2), resized)
    return canvas


def frames_for(src: Path, state: str) -> list[Path]:
    found = sorted(src.glob(f"{state}-*.png"))
    if found:
        return found
    idle = sorted(src.glob("idle-*.png"))
    if not idle:
        raise SystemExit(f"need idle-000.png in {src}")
    print(f"{state}: no frames, using idle")
    return idle


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("frames", type=Path, help="Folder of <state>-NNN.png")
    parser.add_argument("--id", required=True, help="Theme id under themes/custom/")
    parser.add_argument("--name", default="")
    parser.add_argument("--background", default="#071020")
    parser.add_argument("--themes-root", type=Path, default=ROOT / "themes")
    args = parser.parse_args()

    bg = hex_to_rgb(args.background)
    theme_root = args.themes_root / "custom" / args.id
    assets = theme_root / "assets"
    assets.mkdir(parents=True, exist_ok=True)

    states_cfg = {}
    for state in STATES:
        paths = frames_for(args.frames, state)
        images = [fit(Image.open(path), bg) for path in paths]
        dest = assets / f"{state}.gif"
        images[0].save(
            dest,
            save_all=True,
            append_images=images[1:],
            duration=FRAME_MS,
            loop=0,
            disposal=2,
        )
        states_cfg[state] = {
            "animation": f"assets/{state}.gif",
            "loop": state != "stop",
            "caption": state.replace("_", " ").title(),
        }
        print(dest)

    manifest = {
        "id": args.id,
        "name": args.name or args.id,
        "description": "Pixel character generated from a photo. Not the default robot.",
        "display": {
            "width": CANVAS,
            "height": CANVAS,
            "format": "gif",
            "background": args.background,
            "target": "viewe-480",
        },
        "display_mode": "gif",
        "states": states_cfg,
    }
    path = theme_root / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
