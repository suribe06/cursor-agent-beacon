#!/usr/bin/env python3
"""Build 240x240 GIFs for a theme pack from sprite sheets or existing GIFs."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

try:
    from PIL import Image, ImageSequence
except ImportError:
    print(
        "Pillow is required: pip install Pillow",
        file=sys.stderr,
    )
    raise SystemExit(1)


# JaniToad pack: GIF names and PNG folder hints
JANIToad_MAP = {
    "idle.gif": ["idle", "Idle"],
    "walking.gif": ["walking", "walk", "Walk"],
    "attacking.gif": ["attack", "attacking", "Attack"],
    "hurt.gif": ["damage", "hurt", "taking"],
    "death.gif": ["death", "Death"],
}


def find_file(input_dir: Path, hints: list[str]) -> Path | None:
    for path in sorted(input_dir.rglob("*")):
        if not path.is_file():
            continue
        name = path.name.lower()
        if path.suffix.lower() in {".gif", ".png"} and any(
            h.lower() in name for h in hints
        ):
            return path
    return None


def resize_gif(source: Path, dest: Path, size: int) -> None:
    with Image.open(source) as img:
        frames = []
        durations = []
        for frame in ImageSequence.Iterator(img):
            rgba = frame.convert("RGBA")
            resized = rgba.resize((size, size), Image.Resampling.NEAREST)
            frames.append(resized)
            durations.append(frame.info.get("duration", img.info.get("duration", 100)))

        if not frames:
            raise ValueError(f"No frames in {source}")

        frames[0].save(
            dest,
            save_all=True,
            append_images=frames[1:],
            duration=durations,
            loop=0,
            disposal=2,
        )


def copy_or_resize(source: Path, dest: Path, size: int) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if source.suffix.lower() == ".gif":
        resize_gif(source, dest, size)
    else:
        # Single PNG fallback: wrap as 1-frame GIF
        with Image.open(source) as img:
            rgba = img.convert("RGBA")
            resized = rgba.resize((size, size), Image.Resampling.NEAREST)
            resized.save(dest, save_all=True, duration=500, loop=0)


def prepare_janitoad(input_dir: Path, output_dir: Path, size: int) -> list[str]:
    missing: list[str] = []
    assets_dir = output_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    for dest_name, hints in JANIToad_MAP.items():
        source = find_file(input_dir, hints)
        dest = assets_dir / dest_name
        if source is None:
            missing.append(dest_name)
            continue
        copy_or_resize(source, dest, size)
        print(f"  {dest_name} <- {source.name}")

    return missing


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare theme GIF assets")
    parser.add_argument(
        "--input", type=Path, required=True, help="Extracted asset folder"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("themes/standard"),
        help="Theme output directory",
    )
    parser.add_argument(
        "--size", type=int, default=240, help="Square GIF size in pixels"
    )
    parser.add_argument(
        "--pack",
        choices=["janitoad"],
        default="janitoad",
        help="Known asset pack layout",
    )
    args = parser.parse_args()

    if not args.input.is_dir():
        print(f"Input directory not found: {args.input}", file=sys.stderr)
        return 1

    manifest_src = (
        Path(__file__).resolve().parents[1] / "themes" / "standard" / "manifest.json"
    )
    if manifest_src.exists() and args.output.resolve() != manifest_src.parent.resolve():
        shutil.copy2(manifest_src, args.output / "manifest.json")

    print(f"Preparing {args.pack} pack -> {args.output} ({args.size}x{args.size})")
    missing = prepare_janitoad(args.input, args.output, args.size)

    if missing:
        print(
            "\nMissing animations (add manually or check folder names):",
            file=sys.stderr,
        )
        for name in missing:
            print(f"  - {name}", file=sys.stderr)
        return 1

    print("\nDone. Commit themes/standard/assets/*.gif when ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
