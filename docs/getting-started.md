# Getting Started

## Install (recommended)

### From git

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

Then **restart Cursor**. On Ubuntu with GNOME, reload the shell when prompted (`Alt+F2` → `r` on X11, or log out/in on Wayland).

Verify:

```bash
cursor-agent-beacon doctor
cursor-agent-beacon doctor --probe   # optional end-to-end hook test
```

After an Agent chat:

```bash
cursor-agent-beacon status
```

(When using `./setup.sh`, prefix with `.venv/bin/` if the venv is not activated.)

## Uninstall

```bash
cursor-agent-beacon uninstall              # hooks + GNOME panel
cursor-agent-beacon uninstall --purge-status   # also delete status files
```

Restart Cursor after uninstall.

That installs:

- Python package in `.venv/`
- User-level hooks in `~/.cursor/hooks.json` (works in **any** project)
- GNOME top-bar panel on Ubuntu (when available)

Status files:

```bash
cat ~/.local/share/cursor-agent-beacon/status.json
cat ~/.local/share/cursor-agent-beacon/registry.json
```

## Prerequisites

- Python 3.10+
- [Cursor](https://cursor.com) with hooks enabled

## Options

```bash
./setup.sh --hooks-only    # hooks only, no GNOME panel
./setup.sh --no-gnome      # skip GNOME extension
```

After `./setup.sh`, advanced commands are available via `.venv/bin/cursor-agent-beacon` (bridge, map, etc.).

## Verify without Cursor (CLI)

Simulate hook stdin and check the handler response:

```bash
python3 scripts/simulate_hook.py examples/sample-events/before_shell_execution.json
python3 scripts/simulate_hook.py examples/sample-events/stop_completed.json
```

Inspect status mapping only:

```bash
PYTHONPATH=src python3 -m cursor_agent_beacon.cli map examples/sample-events/after_agent_thought.json
```

Run tests:

```bash
pytest
```

## End-to-end test in Cursor

1. Run `./setup.sh` and restart Cursor.
2. Open **any** project (or this repo) in Cursor.
3. Open **Output → Hooks** in the panel below the editor.
4. Start an Agent chat and send any prompt.
5. Check status:

```bash
cat ~/.local/share/cursor-agent-beacon/status.json
```

You should see JSON with `"state"`, `"message"`, and `"hook_event_name"` updating as the agent works.

Optional live watch:

```bash
watch -n 1 cat .cursor-agent-beacon/status.json
```

Structured hook logs also appear in the **Hooks** output channel (stderr JSON lines).

## Preview display theme

```bash
xdg-open preview/display-simulator.html
```

Toggle **Show exported GIF** to view bundled files from `themes/standard/assets/`.

Regenerate GIFs after editing sprites:

```bash
pip install Pillow
python3 scripts/export_standard_gifs.py
```

## Custom GIF theme

See [`themes/custom/README.md`](../themes/custom/README.md).

```bash
export CURSOR_AGENT_BEACON_THEME=your-theme-name
```

## Local bridge (Phase 2)

The bridge is the single owner of the USB serial port. Hook handlers POST status over HTTP; the bridge resolves the theme GIF and writes serial commands for the ESP32 firmware.

**Terminal 1 — start the bridge:**

```bash
pip install -e ".[bridge]"   # only needed when using a real serial port
cursor-agent-beacon bridge
```

**Terminal 2 — forward hook events to the bridge:**

```bash
export CURSOR_AGENT_BEACON_HTTP_URL=http://127.0.0.1:8765/status
python3 scripts/simulate_hook.py examples/sample-events/after_agent_thought.json
```

Without `CURSOR_AGENT_BEACON_SERIAL_PORT`, serial output is logged to stderr:

```text
[cursor-agent-beacon-bridge] serial: THEME|standard
[cursor-agent-beacon-bridge] serial: STATUS|thinking|...
```

**With VIEWE board connected (Linux USB-CDC):**

```bash
cp config/hardware.env.example config/hardware.env
# edit CURSOR_AGENT_BEACON_SERIAL_PORT (often /dev/ttyACM0)

export CURSOR_AGENT_BEACON_SERIAL_PORT=/dev/ttyACM0
export CURSOR_AGENT_BEACON_SERIAL_BAUD=115200
cursor-agent-beacon bridge
```

See [Hardware — VIEWE](hardware-viewe.md) for the full plug-and-play checklist.

Check bridge health:

```bash
curl -s http://127.0.0.1:8765/health | jq
```

## Configuration

| Variable | Default | Description |
|---|---|---|
| `CURSOR_AGENT_BEACON_STATUS_FILE` | `.cursor-agent-beacon/status.json` (project) or `~/.local/share/cursor-agent-beacon/status.json` (user install) | Latest status path |
| `CURSOR_AGENT_BEACON_THEME` | `standard` | Theme id |
| `CURSOR_AGENT_BEACON_THEMES_DIR` | `themes` | Theme packs root |
| `CURSOR_AGENT_BEACON_HTTP_URL` | unset | Bridge endpoint (`http://127.0.0.1:8765/status`) |
| `CURSOR_AGENT_BEACON_BRIDGE_HOST` | `127.0.0.1` | Bridge bind address |
| `CURSOR_AGENT_BEACON_BRIDGE_PORT` | `8765` | Bridge HTTP port |
| `CURSOR_AGENT_BEACON_SERIAL_PORT` | unset | ESP32 serial device |
| `CURSOR_AGENT_BEACON_SERIAL_BAUD` | `115200` | Serial baud rate |

## Next steps

- [Hooks Reference](hooks.md)
- [Display themes](display-themes.md)
- [Architecture](architecture.md)
- [Hardware — VIEWE](hardware-viewe.md)
- [Roadmap](roadmap.md) — VIEWE firmware
