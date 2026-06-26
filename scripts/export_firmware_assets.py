"""Export theme GIFs as firmware-ready frame manifests and PNG sequences.

Reads native 480×480 GIFs from themes/standard/assets/ (see export_standard_gifs.py).
Outputs under firmware/viewe/data/standard/ for LVGL or SPIFFS ingestion.

Requires: pip install Pillow
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

try:
    from PIL import Image, ImageSequence
except ImportError:
    print("Pillow required: pip install Pillow", file=sys.stderr)
    raise SystemExit(1)

from build_character_sprites import DISPLAY_SIZE
from cursor_agent_beacon.theme import load_theme


def export_gif_frames(gif_path: Path, dest_dir: Path) -> list[dict]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    img = Image.open(gif_path)
    if img.size != (DISPLAY_SIZE, DISPLAY_SIZE):
        raise ValueError(
            f"{gif_path} is {img.size[0]}×{img.size[1]}; expected "
            f"{DISPLAY_SIZE}×{DISPLAY_SIZE}. Run: python3 scripts/export_standard_gifs.py"
        )

    frames_meta: list[dict] = []
    for index, frame in enumerate(ImageSequence.Iterator(img)):
        rgba = frame.convert("RGBA")
        out_name = f"frame_{index:02d}.png"
        out_path = dest_dir / out_name
        rgba.save(out_path, format="PNG")
        duration_ms = frame.info.get("duration", img.info.get("duration", 280))
        frames_meta.append(
            {
                "file": out_name,
                "duration_ms": int(duration_ms) if duration_ms else 280,
            }
        )

    return frames_meta


def main() -> int:
    parser = argparse.ArgumentParser(description="Export LVGL-ready theme frames")
    parser.add_argument("--theme", default="standard", help="Theme id (default: standard)")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "firmware" / "viewe" / "data" / "standard",
    )
    args = parser.parse_args()

    theme = load_theme(args.theme, ROOT / "themes")
    states: dict = {}

    for agent_state, animation in theme.animations.items():
        sprite_key = animation.path.stem
        state_dir = args.output / sprite_key
        frames = export_gif_frames(animation.path, state_dir)
        states[agent_state] = {
            "sprite": sprite_key,
            "caption": animation.caption,
            "loop": animation.loop,
            "frames": frames,
        }
        print(f"  {agent_state}: {len(frames)} frames -> {state_dir}")

    manifest = {
        "theme_id": theme.theme_id,
        "display": {
            "width": DISPLAY_SIZE,
            "height": DISPLAY_SIZE,
            "format": "png_sequence",
            "background": theme.manifest.get("display", {}).get("background", "#071020"),
            "target": "viewe-480",
        },
        "states": states,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
