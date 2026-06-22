# Theme packs

Visual GIF themes for the agent status display.

## Standard theme (default, bundled in repo)

Pre-built pixel robot GIFs — one character, animated per agent state.

```text
themes/standard/
  manifest.json
  pixel-faces.json      # sprite source data
  assets/
    sleeping.gif        # idle
    waiting.gif
    thinking.gif
    running_shell.gif
    running_mcp.gif
    success.gif
    error.gif
    stop.gif
```

Regenerate after editing sprites:

```bash
pip install Pillow
python3 scripts/export_standard_gifs.py
```

Preview in browser:

```bash
xdg-open preview/display-simulator.html
```

## Custom themes (your own GIFs)

Personal packs live under `themes/custom/<name>/` (gitignored).

See [`custom/README.md`](custom/README.md) and copy [`custom/example/`](custom/example/).

```bash
export CURSOR_AGENT_BEACON_THEME=pathfinder
```

## Agent state → GIF mapping

| Agent state | Standard GIF |
|---|---|
| `idle` | `sleeping.gif` |
| `waiting` | `waiting.gif` |
| `thinking` | `thinking.gif` |
| `running_shell` | `running_shell.gif` |
| `running_mcp` | `running_mcp.gif` |
| `success` | `success.gif` (soft pulse) |
| `error` | `error.gif` |
| `stop` | `stop.gif` (celebration) |

Python API: `cursor_agent_beacon.theme.load_theme()`.
