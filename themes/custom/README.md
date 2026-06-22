# Custom themes (personal GIF packs)

Drop your own theme folder here. Everything under `custom/` is **gitignored** except this README and the `example/` template.

## Quick setup

```bash
mkdir -p themes/custom/pathfinder/assets
cp themes/custom/example/manifest.json themes/custom/pathfinder/
# Add your GIFs to themes/custom/pathfinder/assets/
# Edit manifest.json animation paths to match your files
```

Enable your theme:

```bash
export CURSOR_AGENT_BEACON_THEME=pathfinder
export CURSOR_AGENT_BEACON_THEMES_DIR=/path/to/cursor-agent-beacon/themes
```

The hook handler and future bridge service resolve GIFs from:

```text
themes/custom/<your-theme-id>/manifest.json
themes/custom/<your-theme-id>/assets/*.gif
```

## Standard theme (default)

Bundled GIFs ship in `themes/standard/assets/`. No setup required.

Regenerate from pixel sprites:

```bash
pip install Pillow
python3 scripts/export_standard_gifs.py
```

## Manifest format

See [`example/manifest.json`](example/manifest.json). Each agent state maps to one GIF:

| Agent state | Typical GIF |
|---|---|
| `idle` | sleeping / standby |
| `waiting` | awaiting prompt |
| `thinking` | reasoning |
| `running_shell` | terminal command |
| `running_mcp` | MCP tool call |
| `success` | step completed |
| `error` | failure |
| `stop` | session finished |

GIF specs for ESP32: **240×240**, loop enabled, keep file size small (<500 KB each).

## Copyright

Do not commit copyrighted characters (e.g. official game assets) to a public fork. Keep personal themes local.
