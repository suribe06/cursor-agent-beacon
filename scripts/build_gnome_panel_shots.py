#!/usr/bin/env python3
"""Render synthetic GNOME panel screenshots (Instrument style, no personal data).

Requires Google Chrome / Chromium. Usage:

  python3 scripts/build_gnome_panel_shots.py
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "images"

CSS = """
:root {
  --panel: #323337;
  --ink: #f2f2f3;
  --mute: rgba(242, 242, 243, 0.55);
  --faint: rgba(242, 242, 243, 0.38);
  --line: rgba(255, 255, 255, 0.08);
  --amber: #e8a35c;
  --steel: #8eb4d4;
  --rose: #e08984;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  width: 336px;
  height: 520px;
  display: grid;
  place-items: center;
  background: #1a1b1e;
  font: 14px/1.4 "Cantarell", "DejaVu Sans", system-ui, sans-serif;
  color: var(--ink);
}
.menu {
  width: 300px;
  height: 484px;
  border-radius: 14px;
  background: var(--panel);
  border: 1px solid var(--line);
  box-shadow: 0 18px 40px rgba(0,0,0,0.4);
  overflow: hidden;
}
.pad { padding: 12px 14px; }
.row { display: flex; align-items: center; gap: 8px; }
.brand { font-size: 0.78rem; color: var(--mute); font-weight: 600; }
.count {
  margin-left: auto;
  font-size: 0.72rem;
  font-weight: 700;
  color: #1a1b1e;
  background: var(--amber);
  padding: 2px 7px;
  min-width: 58px;
  text-align: center;
  border-radius: 999px;
}
.follow { margin-top: 6px; color: var(--mute); font-size: 0.88rem; }
.sep { height: 1px; background: var(--line); margin: 4px 0; }
.hero {
  margin-top: 4px;
  padding: 12px;
  border-radius: 10px;
  background: rgba(0,0,0,0.22);
  border: 1px solid rgba(255,255,255,0.08);
  min-height: 158px;
}
.hero.thinking { border-color: rgba(232,163,92,0.34); }
.hero.working { border-color: rgba(142,180,212,0.34); }
.state { font-size: 1.15rem; font-weight: 700; letter-spacing: -0.02em; }
.state.thinking { color: var(--amber); }
.state.working { color: var(--steel); }
.project { font-size: 0.84rem; color: var(--mute); margin-top: 2px; font-weight: 600; }
.msg { margin-top: 8px; font-size: 0.92rem; min-height: 1.2em; }
.chips {
  display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px;
  min-height: 48px; max-height: 48px; overflow: hidden;
}
.chip {
  font-size: 0.72rem; font-weight: 650; padding: 3px 8px; border-radius: 6px;
  background: rgba(255,255,255,0.06); color: rgba(255,255,255,0.72);
  border: 1px solid var(--line);
}
.chip.ctx { color: rgba(180,210,232,0.95); border-color: rgba(142,180,212,0.35);
  background: rgba(142,180,212,0.1); }
.track {
  margin-top: 10px; height: 4px; border-radius: 999px;
  background: rgba(255,255,255,0.08); overflow: hidden; width: 100%;
}
.fill { height: 100%; border-radius: inherit; background: var(--steel); }
.meta { margin-top: 8px; font-size: 0.75rem; color: var(--faint); min-height: 1em; }
.section {
  font-size: 0.7rem; font-weight: 700; letter-spacing: 0.08em;
  text-transform: uppercase; color: var(--faint); padding: 8px 14px 4px;
}
.session {
  display: flex; gap: 10px; align-items: center;
  padding: 8px 14px; min-height: 40px; font-size: 0.88rem;
}
.dot { width: 7px; height: 7px; border-radius: 50%; flex: none; }
.dot.thinking { background: var(--amber); }
.dot.working { background: var(--steel); }
.dot.idle { background: rgba(255,255,255,0.28); }
.sub { color: var(--faint); font-size: 0.75rem; }
.title { font-weight: 600; }
"""


def page(
    state: str,
    state_label: str,
    project: str,
    message: str,
    chips: list[str],
    ctx_pct: int,
    meta: str,
    sessions: list[tuple[str, str, str]],
) -> str:
    chip_html = "".join(
        f'<span class="chip{" ctx" if "ctx" in c else ""}">{c}</span>' for c in chips
    )
    sess_html = ""
    for style, title, sub in sessions:
        sess_html += (
            f'<div class="session"><span class="dot {style}"></span>'
            f'<div><div class="title">{title}</div>'
            f'<div class="sub">{sub}</div></div></div>'
        )
    # Pad to 3 fixed slots (matches SESSION_SLOTS in the extension).
    for _ in range(max(0, 3 - len(sessions))):
        sess_html += (
            '<div class="session" style="opacity:0">'
            '<span class="dot idle"></span>'
            '<div><div class="title">&nbsp;</div>'
            '<div class="sub">&nbsp;</div></div></div>'
        )

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><style>{CSS}</style></head>
<body>
  <div class="menu" id="shot">
    <div class="pad">
      <div class="row">
        <span class="brand">Cursor Agent</span>
        <span class="count">1 active</span>
      </div>
      <div class="follow">Follow most recent</div>
      <div class="hero {state}">
        <div class="state {state}">{state_label}</div>
        <div class="project">{project}</div>
        <div class="msg">{message}</div>
        <div class="chips">{chip_html}</div>
        <div class="track">
          <div class="fill" style="width:{ctx_pct}%"></div>
        </div>
        <div class="meta">{meta}</div>
      </div>
    </div>
    <div class="sep"></div>
    <div class="section">Open windows</div>
    {sess_html}
  </div>
</body></html>
"""


SHOTS = {
    "gnome-panel-thinking.png": page(
        "thinking",
        "Thinking",
        "demo-workspace",
        "Drafting the Instrument panel layout…",
        ["claude-4.6", "high", "~72% ctx"],
        72,
        "Auto · Thinking · just now · turn 1m12s",
        [
            ("thinking", "demo-workspace", "Thinking · just now · 1m12s"),
            ("idle", "other-repo", "Ready · 12m ago"),
            ("idle", "sandbox-lab", "Ready · 1h ago"),
        ],
    ),
    "gnome-panel-shell.png": page(
        "working",
        "Running shell",
        "demo-workspace",
        "pytest tests/test_display_prefs.py -q",
        ["claude-4.6", "high", "Shell", "~68% ctx"],
        68,
        "Auto · Shell · just now · turn 2m05s",
        [
            ("working", "demo-workspace · focus", "Running shell · just now · 2m05s"),
            ("idle", "other-repo", "Ready · 14m ago"),
            ("idle", "sandbox-lab", "Ready · 1h ago"),
        ],
    ),
}


def find_chrome() -> str:
    for name in (
        "google-chrome",
        "chromium",
        "chromium-browser",
        "google-chrome-stable",
    ):
        path = shutil.which(name)
        if path:
            return path
    raise SystemExit("Chrome/Chromium required to render panel shots")


def render(chrome: str, html: str, dest: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="beacon-shot-") as tmp:
        tmp_path = Path(tmp)
        html_path = tmp_path / "shot.html"
        raw = tmp_path / "raw.png"
        html_path.write_text(html, encoding="utf-8")
        subprocess.run(
            [
                chrome,
                "--headless=new",
                "--disable-gpu",
                "--hide-scrollbars",
                "--window-size=336,520",
                f"--screenshot={raw}",
                html_path.resolve().as_uri(),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            from PIL import Image
        except ImportError as exc:
            raise SystemExit("Pillow required: pip install Pillow") from exc

        img = Image.open(raw).convert("RGBA")
        # Chrome may pad; crop/resize to a stable docs size.
        dest.parent.mkdir(parents=True, exist_ok=True)
        out = (
            img.resize((336, 520), Image.Resampling.LANCZOS)
            if img.size != (336, 520)
            else img
        )
        out.save(dest, optimize=True)
        print(f"wrote {dest.relative_to(ROOT)} ({out.size[0]}×{out.size[1]})")


def main() -> None:
    chrome = find_chrome()
    for name, html in SHOTS.items():
        render(chrome, html, OUT_DIR / name)


if __name__ == "__main__":
    main()
