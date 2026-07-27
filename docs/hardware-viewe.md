# Hardware — VIEWE UEDX48480021 (2.1″ circular)

**This guide is for the VIEWE 2.1″ 480×480 ESP32-S3 round panel** (USB-CDC).  
Other panels: [Hardware displays](hardware.md). Firmware details: [`firmware/viewe/README.md`](../firmware/viewe/README.md).

## Which SKU? (MD80E vs MD80ET)

VIEWE’s catalog naming:

| SKU | Official input | Notes |
| --- | --- | --- |
| **UEDX48480021-MD80E** | Rotary knob, **no** touch | Often sold as “2.1″ Knob” |
| **UEDX48480021-MD80ET** | Rotary knob **+ capacitive touch** | “T” = **Touch**, not “has a taller knob” |

Both catalog SKUs are marketed as **knob** displays (the outer bezel can rotate / press). If your unit has a **touch screen**, treat it as the **ET** family even if the store listing said `MD80E` (common mix-up).

**What this repo flashes:** Arduino board macro `BOARD_VIEWE_UEDX48480021_MD80ET`. That is the init that worked on the unit used for development (factory BBQ demo from the Touch-Knob repo + stable LVGL). Using the plain `MD80E` macro produced a garbled blue screen on that hardware.

Beacon firmware is **display-only** today (GIF + caption). Knob/touch input is not required for agent status.

| | |
| --- | --- |
| Typical Linux port | `/dev/ttyACM0` |
| Baud | **115200** |
| Theme | `standard` GIFs embedded at flash time |

## What you get

- On-device **pixel-robot GIF** per agent state + caption (state + message)
- PC path: Cursor hooks → HTTP → **systemd bridge** → USB serial → panel
- No open terminal required once the bridge service is installed

Knob / touch → `EVENT|...` is **not** required for status display (still deferred).

## Cable and permissions (common failures)

1. Use a **USB-C → USB-A data cable** plugged **directly** into the PC. USB-C docks / USB-C-only hubs often fail to enumerate the Espressif CDC device.
2. Confirm the device: `lsusb` should show Espressif; `ls -l /dev/ttyACM*` should list a port.
3. Your user must be in **`dialout`** (then log out/in):

```bash
sudo usermod -aG dialout $USER
```

## One-time setup

### 0. Desktop package + hooks

From the repo (or after `pip install "cursor-agent-beacon[bridge]"`):

```bash
./setup.sh
# or: cursor-agent-beacon setup
```

Restart Cursor after hooks install.

### 1. Toolchain (flash)

```bash
arduino-cli config add board_manager.additional_urls \
  https://espressif.github.io/arduino-esp32/package_esp32_index.json
arduino-cli core install esp32:esp32@3.1.3
arduino-cli lib install "ESP32_Display_Panel@1.0.3" "lvgl@8.4.0"
```

### 2. Flash firmware

Stop anything holding the serial port (old bridge terminal or `systemctl --user stop cursor-agent-beacon-bridge`).

```bash
cp config/hardware.env.example config/hardware.env
# edit CURSOR_AGENT_BEACON_SERIAL_PORT if not /dev/ttyACM0

export CURSOR_AGENT_BEACON_SERIAL_PORT=/dev/ttyACM0   # used by flash script
./scripts/flash-viewe.sh
```

`flash-viewe.sh` embeds theme GIFs (`scripts/embed_theme_gifs.py`), compiles, and uploads. After reset the panel should show the **idle (sleeping) GIF**.

**Board note:** keep **`BOARD_VIEWE_UEDX48480021_MD80ET`** in `esp_panel_board_supported_conf.h` unless you know you have a no-touch MD80E and the image is wrong. On the touch unit we validated, plain **MD80E** init looked garbled; **MD80ET** worked. (“T” means touch in VIEWE’s naming — both SKUs are still “knob” products in the catalog.)

### 3. Point hooks at the bridge

```bash
set -a && source config/hardware.env && set +a
.venv/bin/cursor-agent-beacon setup --hooks-only \
  --beacon-bin "$(pwd)/.venv/bin/cursor-agent-beacon"
```

Restart Cursor again so the wrapper with `CURSOR_AGENT_BEACON_HTTP_URL` is loaded.

### 4. Run the bridge as a user service (recommended)

```bash
./scripts/install-bridge-service.sh
systemctl --user status cursor-agent-beacon-bridge
# logs: journalctl --user -u cursor-agent-beacon-bridge -f
```

Foreground alternative (dev only):

```bash
set -a && source config/hardware.env && set +a
.venv/bin/cursor-agent-beacon bridge
```

### 5. Verify

```bash
curl -s http://127.0.0.1:8765/health | jq
set -a && source config/hardware.env && set +a
python3 scripts/simulate_hook.py examples/sample-events/after_agent_thought.json
python3 scripts/simulate_hook.py examples/sample-events/before_shell_execution.json
python3 scripts/simulate_hook.py examples/sample-events/stop_completed.json
```

Panel should move **Thinking → Shell → Ready**. Then use a normal Cursor Agent chat; the same path updates the display.

## Day-two ops

| Task | Command |
| --- | --- |
| Bridge status | `systemctl --user status cursor-agent-beacon-bridge` |
| Bridge logs | `journalctl --user -u cursor-agent-beacon-bridge -f` |
| Restart bridge | `systemctl --user restart cursor-agent-beacon-bridge` |
| Reflash | stop bridge → `./scripts/flash-viewe.sh` → start bridge |
| Change theme GIFs | edit sprites → `python3 scripts/export_standard_gifs.py` → reflash |
| Hook / status check | `cursor-agent-beacon doctor` · `cursor-agent-beacon status` |

## Data flow

```text
Cursor hooks → POST /status → bridge (systemd) → /dev/ttyACM0
                                                    ↓
                                      VIEWE firmware (LVGL + GIF)
```

### Serial lines (PC → device)

```text
THEME|standard
STATUS|thinking|Thinking (4200ms)
STATUS|running_shell|npm test
STATUS|success|Ready
```

## Software layers (already in repo)

| Layer | Location |
| --- | --- |
| Hooks → status | `src/cursor_agent_beacon/` |
| HTTP + serial bridge | `cursor-agent-beacon bridge` |
| Theme GIFs 480×480 | `themes/standard/assets/` |
| Embed GIFs into sketch | `scripts/embed_theme_gifs.py` |
| Flash helper | `scripts/flash-viewe.sh` |
| Env template | `config/hardware.env.example` |

## Test without the panel

```bash
python3 scripts/fake_serial_device.py
# use printed /dev/pts/N as CURSOR_AGENT_BEACON_SERIAL_PORT
cursor-agent-beacon bridge
```

## Troubleshooting

| Symptom | Likely fix |
| --- | --- |
| No `/dev/ttyACM*` | Bad cable / dock; try USB-A direct |
| Permission denied on port | `dialout` group + re-login |
| Dark blue / striped screen | Wrong board macro — try `MD80ET` (touch) vs `MD80E`; reflash |
| Idle GIF but no live updates | Bridge not running; hooks missing `HTTP_URL` — re-run setup `--hooks-only`, restart Cursor |
| Stuck on Thinking after reply | Restart Cursor after latest hooks; bridge reconcile decays soft-busy ~20s |
| Port busy on flash | `systemctl --user stop cursor-agent-beacon-bridge` |

## Multi-session focus

The panel follows the same **focused** session as `status.json` / the GNOME panel (`pick_auto_focus`: busiest state, then newest). See [Getting Started](getting-started.md) and registry files under `~/.local/share/cursor-agent-beacon/`.

## Related

- [Hardware displays (hub + other boards)](hardware.md)
- [Firmware README](../firmware/viewe/README.md)
- [Display themes](display-themes.md)
- [Roadmap](roadmap.md)
