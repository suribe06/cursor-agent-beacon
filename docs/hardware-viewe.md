# Hardware — VIEWE Knob Display

Target board: **VIEWE UEDX48480021-MD80E** (ESP32-S3, 480×480 circular IPS, ST7701S, rotary encoder + push button + touch).

## What is already done (no hardware needed)

| Layer | Status | Location |
| --- | --- | --- |
| Cursor hooks → status | ✅ | `src/cursor_agent_beacon/` |
| HTTP bridge | ✅ | `cursor-agent-beacon bridge` |
| Serial writer (`STATUS\|...\`) | ✅ | `bridge/serial_writer.py` |
| Theme GIFs (480×480 native) | ✅ | `themes/standard/assets/` |
| Protocol parser (Python + C++) | ✅ | `protocol.py`, `firmware/viewe/protocol.cpp` |
| Fake serial device | ✅ | `scripts/fake_serial_device.py` |
| Firmware PNG export | ✅ | `scripts/export_firmware_assets.py` |
| Hardware env template | ✅ | `config/hardware.env.example` |
| Firmware sketch skeleton | ✅ | `firmware/viewe/cursor_agent_beacon/` |

## What still needs the physical board

| Task | Why it blocks plug-and-play |
| --- | --- |
| Flash VIEWESMART `examples/2.1inch` | Confirms USB, display driver, baud rate |
| Merge LVGL init into beacon `.ino` | Skeleton only logs serial today |
| Load PNG frames on panel | Needs SPIFFS/LittleFS + `lv_img` |
| Confirm `CURSOR_AGENT_BEACON_SERIAL_PORT` | Real path (`/dev/ttyACM0` on Linux) |

**Not required for first status test:** knob, touch, MCP `EVENT|...` (display-only scope).

## Plug-and-play checklist (day one)

```bash
# 1. Copy and edit serial port
cp config/hardware.env.example config/hardware.env
# set CURSOR_AGENT_BEACON_SERIAL_PORT to your port

# 2. Source env (or export manually)
set -a && source config/hardware.env && set +a

# 3. Terminal A — bridge
pip install -e ".[bridge]"
cursor-agent-beacon bridge

# 4. Terminal B — send status
export CURSOR_AGENT_BEACON_HTTP_URL=http://127.0.0.1:8765/status
python3 scripts/simulate_hook.py examples/sample-events/after_agent_thought.json
```

After firmware shows animations (not just Serial logs), the same bridge command drives the panel from Cursor hooks.

### Linux udev (optional)

If `/dev/ttyACM0` permission is denied, add your user to the `dialout` group:

```bash
sudo usermod -aG dialout $USER
# log out and back in
```

## Data flow

```text
Cursor hooks → hook-handler → POST /status → bridge → USB serial
                                                      ↓
                                            VIEWE firmware (LVGL)
```

## Serial protocol

Baud rate: **115200** default (ESP32-S3 USB-CDC). Confirm in [VIEWESMART examples](https://github.com/VIEWESMART/ESP32-Arduino) before locking production.

### PC → device

```text
THEME|standard
STATUS|thinking|Pensando...
STATUS|running_shell|npm test
STATUS|success|Listo
```

## Test without hardware

```bash
python3 scripts/fake_serial_device.py
# use printed /dev/pts/N as CURSOR_AGENT_BEACON_SERIAL_PORT
cursor-agent-beacon bridge
```

## Regenerate assets (480×480)

```bash
python3 scripts/export_standard_gifs.py      # themes/standard/assets/*.gif
python3 scripts/export_firmware_assets.py    # firmware/viewe/data/standard/
```

Pixel source is still a 24×24 grid; export scale is **×20** → **480×480** GIFs.

## Multi-session display focus

When several Cursor agent chats run at once, the file sink keeps a registry at `.cursor-agent-beacon/registry.json` and writes a **focused** snapshot to `status.json`.

The physical display (bridge → VIEWE) shows the same focused session: the HTTP sink reads `status.json` after the file sink updates it.

### Auto-focus rules (`pick_auto_focus`)

Among **active** sessions only:

1. Prefer the **busiest** state: `thinking` → `running_shell` → `running_mcp` → `waiting` → `error` → `success` → `idle`
2. If tied, prefer the session **updated most recently**

Example: Chat A is `success` (idle) and Chat B is `thinking` → the panel shows **Chat B**.

Fields in `status.json`:

| Field | Meaning |
| --- | --- |
| `focused_conversation_id` | Session shown on the display |
| `active_count` | Active sessions in a busy state |
| `focus_mode` | Always `auto` today |
| `label` / `project` | Human-readable session label |

Per-session files: `.cursor-agent-beacon/sessions/<conversation_id>.json`

## Related

- [Firmware README](../firmware/viewe/README.md)
- [Getting Started](getting-started.md)
- [Roadmap](roadmap.md)
