# Cursor Agent Beacon

[![CI](https://github.com/suribe06/cursor-agent-beacon/actions/workflows/ci.yml/badge.svg)](https://github.com/suribe06/cursor-agent-beacon/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/cursor-agent-beacon.svg)](https://pypi.org/project/cursor-agent-beacon/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

Deterministic monitoring of Cursor agent activity using native [Cursor Hooks](https://cursor.com/docs/hooks).

Cursor fires hook events automatically during the agent lifecycle — the model does not need to report status. Cursor Agent Beacon maps those events to a small set of high-level states and publishes updates through pluggable sinks (file, log, HTTP).

Use it today for a **GNOME top-bar status panel** and CLI (`doctor` / `status`). It is also the software foundation for a **physical status display** (ESP32 + color TFT via the local bridge).

## GNOME status panel

![GNOME top-bar preview](docs/images/gnome-panel-preview.svg)

On Ubuntu/GNOME, the extension reads `~/.local/share/cursor-agent-beacon/` and shows the focused agent session in the top bar (state, tool name, turn timer). See [GNOME Status Panel](docs/gnome-panel.md).

> **Real screenshot:** the image above is an illustration. For a photo from your desktop, capture the top bar after `./setup.sh` and save it as `docs/images/gnome-panel-screenshot.png`, then point the README at that file.

## Quick start

### From git (development)

```bash
git clone https://github.com/suribe06/cursor-agent-beacon.git
cd cursor-agent-beacon
./setup.sh
```

### From PyPI

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install "cursor-agent-beacon[bridge]"
cursor-agent-beacon setup
```

Restart Cursor when setup finishes. On Ubuntu, reload GNOME Shell if the top-bar panel does not appear (`Alt+F2` → `r` on X11, or log out/in on Wayland).

Verify and inspect:

```bash
cursor-agent-beacon doctor
cursor-agent-beacon status    # after an Agent chat
```

Raw status file (any project):

```bash
cat ~/.local/share/cursor-agent-beacon/status.json
```

See [Getting Started](docs/getting-started.md) for bridge, themes, and development setup.

## Features

**Desktop (shipped)**

- One-shot setup: `./setup.sh` or `pip install` + `cursor-agent-beacon setup`
- `doctor` / `status` / `uninstall` CLI
- GNOME status panel (v0.10 pre-release) with multi-session registry
- Normalized states: `idle`, `waiting`, `thinking`, `running_shell`, `running_mcp`, `success`, `error`
- Fail-open hooks — never block Cursor

**Themes & hardware (optional)**

- Standard pixel-robot GIF theme (480×480) in `themes/standard/assets/`
- Custom themes in `themes/custom/<name>/`
- Local bridge (`cursor-agent-beacon bridge`): HTTP → theme GIF → serial (ESP32 / VIEWE)

## Architecture

```text
Cursor → ~/.cursor/hooks.json → cursor-agent-beacon run → mapper → sinks
                                                      ↓
                              ~/.local/share/cursor-agent-beacon/ → GNOME panel
```

Read more in [`docs/architecture.md`](docs/architecture.md).

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `CURSOR_AGENT_BEACON_LOG` | `true` | Emit JSON lines to stderr |
| `CURSOR_AGENT_BEACON_FILE` | `true` | Write latest status file |
| `CURSOR_AGENT_BEACON_STATUS_FILE` | `~/.local/share/cursor-agent-beacon/status.json` (user install) | Status snapshot path |
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
| Python hook handler | ✅ v0.3 |
| One-shot setup + doctor CLI | ✅ v0.3 |
| Multi-session file sink | ✅ v0.3 |
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
./setup.sh
source .venv/bin/activate
pip install -e ".[dev,bridge]"
pytest -m "not smoke"
ruff check src tests
ruff format --check src tests
pyright
python -m build
```

Systemd user service template: [`packaging/cursor-agent-beacon-bridge.service`](packaging/cursor-agent-beacon-bridge.service)

## License

MIT — see [LICENSE](LICENSE).
