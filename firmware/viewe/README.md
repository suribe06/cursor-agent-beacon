# VIEWE UEDX48480021-MD80E firmware

Firmware for the **VIEWE ESP32-S3 Knob Display** (480×480 circular, ST7701S, LVGL).

## Before you have the board

You can still prepare and test:

| Step | Command | What it validates |
| --- | --- | --- |
| Bridge → serial | `scripts/fake_serial_device.py` | Protocol lines without hardware |
| Export frames | `scripts/export_firmware_assets.py` | PNG sequences for LVGL |
| Protocol parser | `protocol.cpp` + unit test on PC (optional) | `STATUS\|...\` parsing |

## When the board arrives

### 1. Arduino IDE setup

1. Install [Arduino ESP32 core](https://docs.espressif.com/projects/arduino-esp32/en/latest/) (ESP32-S3).
2. Library Manager:
   - `ESP32_Display_Panel` (≥ 1.0.3)
   - `lvgl` (8.4.x per VIEWE docs)
3. Clone vendor examples: [VIEWESMART/ESP32-Arduino](https://github.com/VIEWESMART/ESP32-Arduino) → `examples/2.1inch`.
4. Board: **ESP32-S3**. Select the macro for `UEDX48480021-MD80E` in `ESP32_Display_Panel` config.
5. Confirm the **USB serial baud rate** in the vendor example (often `115200` on ESP32-S3 USB-CDC). Match `CURSOR_AGENT_BEACON_SERIAL_BAUD`.

### 2. Flash workflow

1. Open `examples/2.1inch` from VIEWESMART — verify the panel + knob work **before** merging beacon code.
2. Copy initialization from the vendor example into `cursor_agent_beacon/cursor_agent_beacon.ino`.
3. Wire in `protocol.cpp` for serial `STATUS|state|message` lines.
4. Load PNG frames from `data/standard/` (SPIFFS/LittleFS) using `manifest.json`.
5. Map `state` → sprite folder → LVGL `lv_img` animation.

### 3. Connect to the bridge

```bash
# Find port (Linux)
ls /dev/ttyACM* /dev/ttyUSB*

export CURSOR_AGENT_BEACON_SERIAL_PORT=/dev/ttyACM0
export CURSOR_AGENT_BEACON_SERIAL_BAUD=115200
cursor-agent-beacon bridge
```

Send a test status:

```bash
export CURSOR_AGENT_BEACON_HTTP_URL=http://127.0.0.1:8765/status
python3 scripts/simulate_hook.py examples/sample-events/after_agent_thought.json
```

## Serial protocol

See [`docs/hardware-viewe.md`](../../docs/hardware-viewe.md) and Python mirror in `src/cursor_agent_beacon/protocol.py`.

```text
PC → device:  STATUS|<state>|<message>
PC → device:  THEME|<theme_id>
device → PC:  EVENT|button_pressed   (optional, future MCP path)
```

## Asset layout

```text
data/standard/
  manifest.json       # state → sprite → frame list
  thinking/
    frame_00.png
    frame_01.png
    ...
```

Regenerate after theme changes:

```bash
python3 scripts/export_standard_gifs.py
python3 scripts/export_firmware_assets.py
```

## Files in this folder

| File | Purpose |
| --- | --- |
| `protocol.h` / `protocol.cpp` | Parse `STATUS\|...\` lines (portable C++) |
| `cursor_agent_beacon/cursor_agent_beacon.ino` | Sketch skeleton — merge with VIEWESMART init |

## Display-only scope

This repo focuses on **showing agent status**. Knob/button `EVENT|...` lines are defined in the protocol for future use but are not required for the first end-to-end test.
