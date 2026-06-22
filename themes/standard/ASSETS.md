# Standard theme assets

The **standard** theme ships **bundled pixel-robot GIFs** generated from this repository. You do not need to download third-party sprite packs to use the default theme.

## Bundled files

```text
themes/standard/assets/
  sleeping.gif       → agent state: idle
  waiting.gif
  thinking.gif
  running_shell.gif
  running_mcp.gif
  success.gif
  error.gif
  stop.gif
```

Mapping is defined in [`manifest.json`](manifest.json). Sprite source grids live in [`pixel-faces.json`](pixel-faces.json).

## Regenerate GIFs

Edit sprite logic in [`scripts/build_character_sprites.py`](../../scripts/build_character_sprites.py), then export:

```bash
pip install Pillow
python3 scripts/export_standard_gifs.py
```

This updates:

- `themes/standard/assets/*.gif`
- `themes/standard/manifest.json`
- `themes/standard/pixel-faces.json`
- `preview/beacon-sprites.js` (browser preview)

Preview:

```bash
xdg-open preview/display-simulator.html
```

## Animation design (standard theme)

| Agent state | GIF | Behavior |
|---|---|---|
| `idle` | `sleeping.gif` | Slow breath + floating Zzz |
| `waiting` | `waiting.gif` | Awake blink, antenna pulse, glance |
| `thinking` | `thinking.gif` | Yellow thought dots |
| `running_shell` | `running_shell.gif` | Walk cycle + speed lines |
| `running_mcp` | `running_mcp.gif` | Cyan tool link (distinct from thinking) |
| `success` | `success.gif` | Soft green smile pulse |
| `error` | `error.gif` | Shake, then hold |
| `stop` | `stop.gif` | Wave + confetti |

## Custom themes (replace with your own GIFs)

For personal packs (e.g. a different character), use [`../custom/`](../custom/). Drop 240×240 GIFs and a `manifest.json` — see [`../custom/example/`](../custom/example/).

```bash
export CURSOR_AGENT_BEACON_THEME=your-theme-name
```

Custom theme folders are gitignored so copyrighted assets stay local.

## Display target

- **240×240 color TFT** (ST7789 or GC9A01 round)
- Visual only — no audio
- Optional caption line under the character (planned in firmware)

## Third-party asset references (optional)

If you want to build a **custom** theme from external art instead of editing our pixel generator, these CC0 packs are good starting points:

| Pack | URL | License |
|---|---|---|
| JaniToad 2D Robot | https://janitoad.itch.io/2d-robot-character | CC0 |
| Foozle Colorful Robot | https://foozlecc.itch.io/colorful-robot-action-pack | CC0 |
| Foozle Cute Platformer Robot | https://foozlecc.itch.io/cute-platformer-robot | CC0 |

Do **not** commit copyrighted characters (e.g. official game assets) to a public repository.

Convert external sprites to 240×240 GIFs with [ezgif.com](https://ezgif.com/resize) and place them in `themes/custom/<name>/assets/`.
