# Display preview

Interactive simulator for the 240×240 agent display.

## Open the simulator

```bash
# From repo root — open in browser (both files must stay in preview/)
xdg-open preview/display-simulator.html
```

Sprites are built at runtime by `preview/sprite-builder.js` (full 24×24 body + face, 4 frames per state).

To export static PNGs for firmware:

```bash
pip install Pillow
python3 scripts/build_character_sprites.py   # writes themes/standard/pixel-faces.json
python3 scripts/generate_pixel_faces.py      # optional PNG export
```

## What it shows

**Hybrid display model:**

1. **Robot body** — placeholder silhouette (future: CC0 GIF underneath)
2. **Pixel face overlay** — changes per agent state for instant readability

### Idle = sleeping

When Cursor is doing nothing, the display shows a **sleeping face** with animated floating `Zzz` — not a generic idle loop. This reads clearly on a small round screen.

### Pixel faces per state

| Face | Agent state | Visual cue |
| --- | --- | --- |
| Sleeping | `idle` | Closed eyes + Zzz animation |
| Waiting | `waiting` | Open eyes, neutral mouth |
| Thinking | `thinking` | Thought dots above head |
| Running shell | `running_shell` | Focused eyes + motion lines |
| MCP tool | `running_mcp` | Star/spark accent |
| Success | `success` | Green smile |
| Error | `error` | Red X eyes |
| Done | `stop` | Calm closed eyes + green smile |

Face definitions live in [`../themes/standard/pixel-faces.json`](../themes/standard/pixel-faces.json).

## Export PNG sprites for firmware

```bash
pip install Pillow
python3 scripts/generate_pixel_faces.py
```

Output: `themes/standard/assets/faces/*.png`

## Controls in the simulator

- Click any state on the left panel
- **Auto cycle** — rotates through all states
- **Round display** — toggles round bezel (GC9A01 style)
