#!/usr/bin/env python3
"""Export standard theme GIFs from the eye sprite definitions."""

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

from build_character_sprites import (  # noqa: E402
    BG,
    DISPLAY_SIZE,
    build_faces,
    frame_durations,
    state_map,
    write_preview_bundle,
)

ROOT = Path(__file__).resolve().parents[1]
BG_HEX = "#{:02x}{:02x}{:02x}".format(*BG)


def export_gif(frames: list[Image.Image], dest: Path, sprite_key: str) -> None:
    durations = frame_durations(sprite_key, len(frames))
    rgb = [frame.convert("RGB") for frame in frames]
    rgb[0].save(
        dest,
        save_all=True,
        append_images=rgb[1:],
        duration=durations,
        loop=0,
        disposal=2,
        optimize=True,
    )


def write_manifest(faces: dict) -> Path:
    manifest_path = ROOT / "themes" / "standard" / "manifest.json"
    states_cfg: dict = {}
    for agent_state, sprite_key in state_map().items():
        face = faces[sprite_key]
        states_cfg[agent_state] = {
            "animation": f"assets/{sprite_key}.gif",
            "loop": agent_state != "stop",
            "caption": face["caption"],
        }

    manifest = {
        "id": "standard",
        "name": "Beacon Eyes",
        "description": "Default expressive-eye GIFs bundled with the repository",
        "license": "MIT",
        "author": "cursor-agent-beacon",
        "display": {
            "width": DISPLAY_SIZE,
            "height": DISPLAY_SIZE,
            "format": "gif",
            "background": BG_HEX,
            "target": "viewe-480",
        },
        "display_mode": "gif",
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
    write_preview_bundle(faces)

    args.output.mkdir(parents=True, exist_ok=True)
    for sprite_key, face in faces.items():
        dest = args.output / f"{sprite_key}.gif"
        export_gif(face["frames"], dest, sprite_key)
        print(f"  {dest}")

    manifest = write_manifest(faces)
    print(f"Wrote {manifest}")
    print(f"\nExported {len(faces)} GIFs to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
