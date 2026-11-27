# Display themes

Each theme is a folder with `manifest.json` + `assets/*.gif` (**480×480** for the VIEWE desk panel and the browser simulator).

## Standard theme (default, in repo)

Bundled **eye** GIFs (the default face) generated from `scripts/build_character_sprites.py`:

| Agent state | GIF | Animation |
|---|---|---|
| `idle` | `sleeping.gif` | Eyes drift shut |
| `waiting` | `waiting.gif` | Happy eyes, glance, blink |
| `thinking` | `thinking.gif` | Eyes look up and around |
| `running_shell` | `running_shell.gif` | Narrow eyes scanning |
| `running_mcp` | `running_mcp.gif` | Steady eyes, green spark |
| `success` | `success.gif` | Smile that pulses |
| `error` | `error.gif` | Shock, then a sweat drop |
| `stop` | `stop.gif` | Laughing eyes |

Regenerate:

```bash
pip install Pillow
python3 scripts/export_standard_gifs.py
```

Preview:

```bash
xdg-open preview/display-simulator.html
```

The simulator plays the GIFs from `themes/standard/assets/`.

## Custom themes (your own GIFs)

1. Copy `themes/custom/example/` → `themes/custom/<your-theme>/`
2. Replace GIFs in `assets/`
3. Edit `manifest.json` paths if needed
4. Enable:

```bash
export CURSOR_AGENT_BEACON_THEME=your-theme
export CURSOR_AGENT_BEACON_THEMES_DIR=/path/to/cursor-agent-beacon/themes
```

Custom folders are **gitignored** (safe for Pathfinder or other personal assets).

## Python API

```python
from cursor_agent_beacon.theme import load_theme

theme = load_theme("standard")
anim = theme.animation_for("idle")
print(anim.path)  # .../themes/standard/assets/sleeping.gif
```

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `CURSOR_AGENT_BEACON_THEME` | `standard` | Theme folder name under `standard/` or `custom/` |
| `CURSOR_AGENT_BEACON_THEMES_DIR` | `themes` | Root directory containing theme packs |
