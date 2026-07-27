# VIEWE UEDX48480021 firmware (2.1″ circular)

**Board-specific** firmware for the VIEWE ESP32-S3 480×480 round panel (LVGL + embedded GIFs).  
Setup: [`docs/hardware-viewe.md`](../../docs/hardware-viewe.md) · other displays: [`docs/hardware.md`](../../docs/hardware.md).

SKU note: VIEWE **MD80E** = knob without touch, **MD80ET** = knob + touch. This sketch selects `BOARD_VIEWE_UEDX48480021_MD80ET` because that panel init worked on the touch unit we tested (plain `MD80E` looked garbled). Beacon UI does not need the rotary ring.

## Requirements

- [arduino-cli](https://arduino.github.io/arduino-cli/) or Arduino IDE
- ESP32 Arduino core ≥ 3.1
- Libraries (Library Manager):
  - `ESP32_Display_Panel` ≥ 1.0.3 (+ deps)
  - `lvgl` 8.4.x

```bash
arduino-cli config add board_manager.additional_urls \
  https://espressif.github.io/arduino-esp32/package_esp32_index.json
arduino-cli core install esp32:esp32@3.1.3
arduino-cli lib install "ESP32_Display_Panel@1.0.3" "lvgl@8.4.0"
```

Board macro in `cursor_agent_beacon/esp_panel_board_supported_conf.h`:

```c
#define ESP_PANEL_BOARD_DEFAULT_USE_SUPPORTED (1)
#define BOARD_VIEWE_UEDX48480021_MD80ET
```

Use **`MD80ET`** unless you have confirmed a no-touch MD80E that needs the other macro. (“T” = touch in VIEWE naming.)

## Flash (Linux USB CDC)

Port is usually `/dev/ttyACM0`. Prefer a **USB-C → USB-A** cable **direct to the PC** (docks often fail). User must be in group `dialout`. Stop the bridge service before upload.

```bash
./scripts/flash-viewe.sh
# or:
FQBN='esp32:esp32:esp32s3:UploadSpeed=921600,USBMode=hwcdc,CDCOnBoot=cdc,FlashMode=qio,FlashSize=16M,PartitionScheme=app3M_fat9M_16MB,PSRAM=opi,DebugLevel=info,EraseFlash=all'
arduino-cli compile --fqbn "$FQBN" firmware/viewe/cursor_agent_beacon
arduino-cli upload -p /dev/ttyACM0 --fqbn "$FQBN" firmware/viewe/cursor_agent_beacon
```

After flash, the panel should show the **idle (sleeping) GIF**.

## Connect to the bridge

See the checklist in [`docs/hardware-viewe.md`](../../docs/hardware-viewe.md). Short version:

```bash
cp config/hardware.env.example config/hardware.env
set -a && source config/hardware.env && set +a
cursor-agent-beacon setup --hooks-only --beacon-bin "$(pwd)/.venv/bin/cursor-agent-beacon"
./scripts/install-bridge-service.sh   # or: cursor-agent-beacon bridge
```

## Serial protocol

```text
PC → device:  STATUS|<state>|<message>
PC → device:  THEME|<theme_id>
```

## Files

| Path | Purpose |
| --- | --- |
| `cursor_agent_beacon/*.ino` + LVGL port | GIF + status UI |
| `cursor_agent_beacon/theme_gifs.*` | Generated embedded GIFs (`embed_theme_gifs.py`) |
| `cursor_agent_beacon/protocol.*` | `STATUS\|...` parser |
| `../protocol.*` | Same parser (reference / non-Arduino builds) |

## Display-only scope

Knob/button `EVENT|...` still deferred.
