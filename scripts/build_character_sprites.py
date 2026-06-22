#!/usr/bin/env python3
"""Build full-body 24x24 robot sprites and optional preview bundle."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GRID = 24
BG_HEX = "#071020"

# Blue desk-setup palette: navy background, cobalt body, sky/cyan accents.
PALETTE: dict[str, str | None] = {
    ".": None,
    "#": "#0c1929",
    "H": "#152238",
    "F": "#2563eb",
    "B": "#1d4ed8",
    "b": "#38bdf8",
    "L": "#0a1628",
    "A": "#60a5fa",
    "a": "#1e40af",
    "E": "#dbeafe",
    "e": "#475569",
    "M": "#7c3aed",
    "m": "#1e3a8a",
    "G": "#22d3ee",
    "Y": "#7dd3fc",
    "Z": "#94a3b8",
    "S": "#0ea5e9",
    "T": "#06b6d4",
}


def blank() -> list[str]:
    return ["." * GRID for _ in range(GRID)]


def stamp(grid: list[str], x: int, y: int, art: list[str]) -> None:
    for dy, row in enumerate(art):
        gy = y + dy
        if gy < 0 or gy >= GRID:
            continue
        line = list(grid[gy])
        for dx, ch in enumerate(row):
            gx = x + dx
            if 0 <= gx < GRID and ch != " ":
                line[gx] = ch
        grid[gy] = "".join(line)


def robot_base(
    *,
    eyes: str = "EE",
    mouth: str = "mm",
    arm_left: str = "Aa",
    arm_right: str = "aA",
    leg_offset: int = 0,
    bob: int = 0,
    head_shift: int = 0,
) -> list[str]:
    g = blank()
    y = 3 + bob
    e1, e2 = eyes[0], eyes[1]
    m1, m2 = mouth[0], mouth[1]
    hx = 7 + head_shift
    head = [
        "....HH....",
        "..HFFFFH..",
        ".HFFFFFFH.",
        f"HF##{e1}{e2}##FH",
        f"HF##{e1}{e2}##FH",
        f"HF#{m1}{m2}##FH",
        "..HHFFHH..",
    ]
    stamp(g, hx, y, head)
    stamp(g, 10 + head_shift, y + 7, ["..HBBH.."])
    stamp(g, 7, y + 8, [f"{arm_left}.BBBB.{arm_right}"])
    stamp(g, 8, y + 9, ["..BBBBBB.."])
    stamp(g, 8, y + 10, ["..BBBBBB.."])
    lx = 9 - leg_offset
    rx = 14 + leg_offset
    for row in range(3):
        stamp(g, lx, y + 11 + row, ["..LL.."])
        stamp(g, rx, y + 11 + row, ["..LL.."])
    return g


def add_zzz(grid: list[str], frame: int) -> None:
    arts = [
        ["..ZZZ", ".ZZZ."],
        [".ZZZ.", "..ZZZ"],
        ["..ZZ.", ".ZZZ.", "..ZZ"],
        ["..ZZZ", "..ZZZ"],
    ]
    stamp(grid, 8 + (frame % 2), 1, arts[frame % 4])


def add_thought_dots(grid: list[str], frame: int) -> None:
    """Light blue thought dots above the head."""
    arts = [
        ["Y.Y.Y", ".Y.Y."],
        [".Y.Y.", "Y.Y.Y"],
        ["..Y.Y", ".Y.Y."],
        ["Y.Y..", ".Y.Y."],
    ]
    stamp(grid, 9 + (frame % 2), 1, arts[frame % 4])


def add_tool_link(grid: list[str], frame: int) -> None:
    """Cyan tool-link spark (distinct from thinking dots)."""
    arts = [
        ["..T..", ".T.T.", "..T.."],
        [".T.T.", "..T..", ".Tb."],
        ["T.T.T", "..Tb.", "T.T.T"],
        [".TbT.", "T.T.T", ".Tb."],
    ]
    stamp(grid, 9, 1, arts[frame % 4])


def add_speed(grid: list[str], frame: int) -> None:
    if frame % 2 == 0:
        stamp(grid, 0, 14, ["S", "S"])
        stamp(grid, 22, 14, ["S", "S"])
    else:
        stamp(grid, 1, 16, ["S"])
        stamp(grid, 21, 16, ["S"])


def add_confetti(grid: list[str], frame: int) -> None:
    if frame in {1, 2}:
        stamp(grid, 8, 1, ["Y", "Y"])
        stamp(grid, 16, 2, ["Y", "G"])


def add_antenna_pulse(grid: list[str], frame: int, y: int) -> None:
    if frame % 2 == 0:
        stamp(grid, 11, y - 1, ["..b.."])
    else:
        stamp(grid, 11, y - 1, [".bbb."])


def shift_grid(grid: list[str], dx: int, dy: int = 0) -> list[str]:
    out = blank()
    for y, row in enumerate(grid):
        for x, ch in enumerate(row):
            if ch == ".":
                continue
            nx, ny = x + dx, y + dy
            if 0 <= nx < GRID and 0 <= ny < GRID:
                line = list(out[ny])
                line[nx] = ch
                out[ny] = "".join(line)
    return out


def shift_x(grid: list[str], dx: int) -> list[str]:
    return shift_grid(grid, dx, 0)


def _union_bbox(grids: list[list[str]]) -> tuple[int, int, int, int] | None:
    min_x = min_y = GRID
    max_x = max_y = -1
    for grid in grids:
        for y, row in enumerate(grid):
            for x, ch in enumerate(row):
                if ch == ".":
                    continue
                min_x = min(min_x, x)
                max_x = max(max_x, x)
                min_y = min(min_y, y)
                max_y = max(max_y, y)
    if max_x < 0:
        return None
    return min_x, min_y, max_x, max_y


def center_animation(
    grids: list[list[str]],
    *,
    optical_bias_y: int = 1,
) -> list[list[str]]:
    """Center all frames using the animation union bbox (avoids frame jitter)."""
    bbox = _union_bbox(grids)
    if bbox is None:
        return grids

    min_x, min_y, max_x, max_y = bbox
    cx = (min_x + max_x) / 2
    cy = (min_y + max_y) / 2
    target = (GRID - 1) / 2
    dx = round(target - cx)
    dy = round(target - cy) + optical_bias_y
    dx = max(-min_x, min(dx, GRID - 1 - max_x))
    dy = max(-min_y, min(dy, GRID - 1 - max_y))
    if dx == 0 and dy == 0:
        return grids
    return [shift_grid(grid, dx, dy) for grid in grids]


def frames_to_strings(frames: list[list[str]]) -> list[str]:
    result: list[str] = []
    for grid in frames:
        for y, row in enumerate(grid):
            if len(row) != GRID:
                raise ValueError(f"Row {y} width {len(row)} != {GRID}: {row}")
        if len(grid) != GRID:
            raise ValueError(f"Grid height {len(grid)} != {GRID}")
        result.append("\n".join(grid))
    return result


def build_faces() -> dict:
    # Idle: slow breathing + Zzz (closed eyes only here)
    sleeping: list[list[str]] = []
    for i in range(4):
        g = robot_base(eyes="ee", mouth="mm", bob=i % 2)
        add_zzz(g, i)
        sleeping.append(g)

    # Waiting: awake, antenna pulse, glance left/right, quick blink never fully asleep
    waiting: list[list[str]] = []
    for i in range(4):
        eyes = "E." if i == 2 else "EE"
        g = robot_base(
            eyes=eyes,
            mouth="..",
            head_shift=[-1, 0, 1, 0][i],
            bob=0,
        )
        add_antenna_pulse(g, i, 3)
        waiting.append(g)

    thinking: list[list[str]] = []
    for i in range(4):
        g = robot_base(eyes="EE", mouth="mm", arm_left="A." if i % 2 else ".A")
        add_thought_dots(g, i)
        thinking.append(g)

    running_shell: list[list[str]] = []
    for i in range(4):
        g = robot_base(
            eyes="EE",
            mouth="MM",
            leg_offset=[0, 1, 0, -1][i],
            arm_left="A.",
            arm_right=".A",
        )
        add_speed(g, i)
        running_shell.append(g)

    running_mcp: list[list[str]] = []
    for i in range(4):
        g = robot_base(eyes="EE", mouth="MM", arm_left="A.", arm_right="..")
        add_tool_link(g, i)
        stamp(g, 8, 9, ["..b..", ".bbb.", "..b.."] if i % 2 else [".bbb.", "..b.."])
        running_mcp.append(g)

    # Soft success: gentle smile pulse only
    success: list[list[str]] = []
    for i in range(4):
        mouth = "GG" if i % 2 == 0 else "G."
        g = robot_base(eyes="EE", mouth=mouth, bob=i % 2)
        success.append(g)

    # Error: 3 shakes then hold static pose (6 frames)
    error: list[list[str]] = []
    shake_dx = [-1, 1, -1]
    for dx in shake_dx:
        error.append(shift_x(robot_base(eyes="MM", mouth="MM"), dx))
    settled = robot_base(eyes="MM", mouth="MM")
    error.extend([settled, settled, settled])

    # Stop / session done: full celebration
    stop: list[list[str]] = []
    for i in range(4):
        wave = ("A..", "..A") if i in {1, 2} else ("Aa", "aA")
        g = robot_base(
            eyes="EE",
            mouth="GG",
            arm_left=wave[0],
            arm_right=wave[1],
            bob=1 if i == 1 else 0,
        )
        add_confetti(g, i)
        stop.append(g)

    meta = {
        "sleeping": ("Sleeping", "Idle — slow breath + Zzz"),
        "waiting": ("Waiting", "Awake — antenna pulse + glance"),
        "thinking": ("Thinking", "Sky-blue thought dots"),
        "running_shell": ("Running shell", "Walk cycle + speed lines"),
        "running_mcp": ("MCP tool", "Cyan tool link + chest pulse"),
        "success": ("Success", "Soft cyan smile pulse"),
        "error": ("Error", "Shake then hold"),
        "stop": ("Session done", "Wave + confetti"),
    }

    built: dict = {}
    for key, grid_frames in [
        ("sleeping", sleeping),
        ("waiting", waiting),
        ("thinking", thinking),
        ("running_shell", running_shell),
        ("running_mcp", running_mcp),
        ("success", success),
        ("error", error),
        ("stop", stop),
    ]:
        label, caption = meta[key]
        grid_frames = center_animation(grid_frames)
        built[key] = {
            "label": label,
            "caption": caption,
            "frames": frames_to_strings(grid_frames),
        }
    return built


def frame_durations(sprite_key: str, frame_count: int) -> list[int]:
    if sprite_key == "sleeping":
        return [700] * frame_count
    if sprite_key == "error" and frame_count >= 6:
        return [120, 120, 120, 500, 500, 500]
    if sprite_key == "success":
        return [350] * frame_count
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


def write_pixel_faces(faces: dict) -> Path:
    path = ROOT / "themes" / "standard" / "pixel-faces.json"
    payload = {
        "version": 1,
        "grid_size": GRID,
        "palette": {k: v if v else "transparent" for k, v in PALETTE.items()},
        "faces": faces,
        "state_map": state_map(),
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def write_preview_bundle(faces: dict) -> Path:
    path = ROOT / "preview" / "beacon-sprites.js"
    bundle = {
        "grid_size": GRID,
        "palette": PALETTE,
        "faces": faces,
    }
    js = (
        "/** Auto-generated by scripts/build_character_sprites.py — do not edit. */\n"
        "window.BEACON_SPRITES = "
        + json.dumps(bundle, indent=2)
        + ";\n"
    )
    path.write_text(js, encoding="utf-8")
    return path


def main() -> int:
    faces = build_faces()
    print(f"Wrote {write_pixel_faces(faces)}")
    print(f"Wrote {write_preview_bundle(faces)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
