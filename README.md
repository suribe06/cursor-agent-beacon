# Cursor Agent Beacon

[![CI](https://github.com/suribe06/cursor-agent-beacon/actions/workflows/ci.yml/badge.svg)](https://github.com/suribe06/cursor-agent-beacon/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

Deterministic monitoring of Cursor agent activity using native [Cursor Hooks](https://cursor.com/docs/hooks).

**Repository:** https://github.com/suribe06/cursor-agent-beacon

Cursor fires hook events automatically during the agent lifecycle. Cursor Agent Beacon listens to those events, maps them to a small set of high-level states, and publishes status updates through pluggable sinks.

This is the software foundation for a physical status panel (ESP32 + color TFT). **v0.2** ships Python hooks, **bundled standard GIF themes**, and a **local bridge service**.

## Features

- Single hook handler for agent lifecycle events
- Normalized status model (`idle`, `thinking`, `running_shell`, `running_mcp`, `success`, `error`, ...)
- **Standard theme**: 8 animated pixel-robot GIFs (480×480) in `themes/standard/assets/`
- **Custom themes**: drop your own GIFs in `themes/custom/<name>/`
- Fail-open behavior — hooks never block Cursor
- JSON log sink (stderr) for the Hooks output channel
- File sink with latest status snapshot
- HTTP sink for the local bridge service
- **Bridge service** (`cursor-agent-beacon bridge`): `POST /status` → theme GIF resolution → serial commands
- **GNOME status panel** (v0.10, pre-release): Ubuntu top-bar indicator — [`gnome-extension/`](gnome-extension/) + [`docs/gnome-panel.md`](docs/gnome-panel.md)
- **Multi-session registry**: per-chat status under `~/.local/share/cursor-agent-beacon/`

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

# Run the local bridge (dry-run serial logs to stderr)
cursor-agent-beacon bridge

# Forward hook status to the bridge
export CURSOR_AGENT_BEACON_HTTP_URL=http://127.0.0.1:8765/status
python3 scripts/simulate_hook.py examples/sample-events/after_agent_thought.json

# Install globally (hooks + GNOME panel)
cursor-agent-beacon install-desktop
# or: ./scripts/install-desktop.sh
```

Open this repository in Cursor to activate the bundled `.cursor/hooks.json`.

**Ubuntu desktop (hooks + GNOME panel):**

```bash
./scripts/install-desktop.sh
# Alt+F2 → r to reload GNOME Shell
```

Global status (any Cursor project):

```bash
cat ~/.local/share/cursor-agent-beacon/status.json
cat ~/.local/share/cursor-agent-beacon/registry.json
```

Project-local status (when using repo hooks without install-user-hooks):

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
| `CURSOR_AGENT_BEACON_STATUS_FILE` | `.cursor-agent-beacon/status.json` (project) or `~/.local/share/cursor-agent-beacon/status.json` (user install) | Status snapshot path |
| `CURSOR_AGENT_BEACON_HTTP_URL` | unset | Bridge `POST /status` endpoint |
| `CURSOR_AGENT_BEACON_BRIDGE_HOST` | `127.0.0.1` | Bridge bind address |
| `CURSOR_AGENT_BEACON_BRIDGE_PORT` | `8765` | Bridge HTTP port |
| `CURSOR_AGENT_BEACON_SERIAL_PORT` | unset | ESP32 serial device (dry-run if unset) |
| `CURSOR_AGENT_BEACON_SERIAL_BAUD` | `115200` | Serial baud rate |
| `CURSOR_AGENT_BEACON_THEME` | `standard` | Theme id (`standard` or custom theme name) |
| `CURSOR_AGENT_BEACON_THEMES_DIR` | packaged `themes/` or repo `themes/` | Root folder for theme packs |
| `CURSOR_AGENT_BEACON_REDACT_CONTENT` | `false` | Hide prompt/response text in status |

## Project status

| Component | Status |
| --- | --- |
| Python hook handler | ✅ v0.2 |
| Multi-session file sink | ✅ v0.2 |
| GNOME status panel | 🧪 v0.10 pre-release |
| Standard GIF theme | ✅ bundled |
| Custom GIF themes | ✅ `themes/custom/` |
| Local bridge service | ✅ v0.2 |
| VIEWE display firmware | 🔜 planned |

See [`docs/roadmap.md`](docs/roadmap.md).

## Documentation

- [Getting Started](docs/getting-started.md)
- [Hooks Reference](docs/hooks.md)
- [GNOME Status Panel](docs/gnome-panel.md)
- [Architecture](docs/architecture.md)
- [Hardware — VIEWE](docs/hardware-viewe.md)
- [Roadmap](docs/roadmap.md)
- [Changelog](CHANGELOG.md)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Please read the [Code of Conduct](CODE_OF_CONDUCT.md) before participating.

Report security issues privately — see [SECURITY.md](SECURITY.md).

## Development

```bash
pip install -e ".[dev,bridge]"
pytest
ruff check src tests
ruff format --check src tests
pyright
python -m build
cursor-agent-beacon bridge
cursor-agent-beacon install-hooks
PYTHONPATH=src python3 -m cursor_agent_beacon.cli map examples/sample-events/stop_completed.json
```

Systemd user service template: [`packaging/cursor-agent-beacon-bridge.service`](packaging/cursor-agent-beacon-bridge.service)

## License

MIT — see [LICENSE](LICENSE).
