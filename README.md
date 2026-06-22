# Cursor Agent Beacon

Deterministic monitoring of Cursor agent activity using native [Cursor Hooks](https://cursor.com/docs/hooks).

Cursor fires hook events automatically during the agent lifecycle. Cursor Agent Beacon listens to those events, maps them to a small set of high-level states, and publishes status updates through pluggable sinks.

This is the software foundation for a physical status panel (ESP32 + color TFT). **v0.1** ships Python hooks plus **bundled standard GIF themes**.

## Features

- Single hook handler for agent lifecycle events
- Normalized status model (`idle`, `thinking`, `running_shell`, `running_mcp`, `success`, `error`, ...)
- **Standard theme**: 8 animated pixel-robot GIFs (240×240) in `themes/standard/assets/`
- **Custom themes**: drop your own GIFs in `themes/custom/<name>/`
- Fail-open behavior — hooks never block Cursor
- JSON log sink (stderr) for the Hooks output channel
- File sink with latest status snapshot
- HTTP sink stub for a future local bridge service

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Preview display + exported GIFs
xdg-open preview/display-simulator.html

# Regenerate standard GIFs after editing sprites
pip install Pillow
python3 scripts/export_standard_gifs.py
```

Open this repository in Cursor to activate the bundled `.cursor/hooks.json`.

Latest status snapshot:

```bash
cat .cursor-agent-beacon/status.json
```

## Architecture

```text
Cursor → hooks.json → hook-handler.py → cursor_agent_beacon → sinks
```

Read more in [`docs/architecture.md`](docs/architecture.md).

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `CURSOR_AGENT_BEACON_LOG` | `true` | Emit JSON lines to stderr |
| `CURSOR_AGENT_BEACON_FILE` | `true` | Write latest status file |
| `CURSOR_AGENT_BEACON_STATUS_FILE` | `.cursor-agent-beacon/status.json` | Status file path |
| `CURSOR_AGENT_BEACON_HTTP_URL` | unset | Optional bridge endpoint |
| `CURSOR_AGENT_BEACON_THEME` | `standard` | Theme id (`standard` or `custom/<name>`) |
| `CURSOR_AGENT_BEACON_THEMES_DIR` | `themes` | Root folder for theme packs |

## Project status

| Component | Status |
| --- | --- |
| Python hook handler | ✅ v0.1 |
| Standard GIF theme | ✅ bundled |
| Custom GIF themes | ✅ `themes/custom/` |
| Arduino firmware | 🔜 planned |
| MCP button input | 🔜 planned |
| Local bridge service | 🔜 planned |

See [`docs/roadmap.md`](docs/roadmap.md).

## Documentation

- [Getting Started](docs/getting-started.md)
- [Hooks Reference](docs/hooks.md)
- [Architecture](docs/architecture.md)

## Development

```bash
pip install -e ".[dev]"
pytest
PYTHONPATH=src python3 -m cursor_agent_beacon.cli map examples/sample-events/stop_completed.json
```

## License

MIT — see [LICENSE](LICENSE).

## Contributing

Contributions welcome. This project is intentionally small and focused: deterministic status from Cursor hooks first, hardware integration later.
