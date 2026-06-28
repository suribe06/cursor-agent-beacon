# Roadmap

## Phase 1 — Python hooks ✅

- [x] Normalize Cursor hook events into agent status
- [x] Pluggable sinks (log, file, HTTP stub)
- [x] Project-level `.cursor/hooks.json`
- [x] Local simulation script and tests

## Phase 1.5 — Standard display theme ✅

- [x] Pixel robot sprite generator (`scripts/build_character_sprites.py`)
- [x] Export 480×480 GIFs (`scripts/export_standard_gifs.py`)
- [x] `themes/standard/manifest.json` + bundled assets
- [x] Custom theme layout (`themes/custom/`)
- [x] Theme loader (`cursor_agent_beacon.theme`)
- [x] Browser preview (`preview/display-simulator.html`)

## Phase 2 — Local bridge service ✅

- [x] Long-running Python service
- [x] `POST /status` endpoint for hook handler
- [x] Resolve GIF from theme pack per agent state
- [x] Serial writer thread for ESP32 commands
- [x] Single owner of the USB serial port

## Phase 2.5 — GNOME desktop panel 🧪

Target: Ubuntu / GNOME Shell 46+ top-bar indicator (pre-release v0.10).

- [x] Multi-session registry on disk (`~/.local/share/cursor-agent-beacon/`)
- [x] GNOME Shell extension (`gnome-extension/`)
- [x] User-level hook installer (`scripts/install-user-hooks.sh`)
- [x] Session pin menu + human-readable timestamps
- [ ] Stable panel position across shell restarts
- [ ] Turn timer (`startedAt`) in panel

Install: `./scripts/install-desktop.sh` · Docs: [`gnome-panel.md`](gnome-panel.md)

## Phase 3 — VIEWE display firmware (ESP32-S3 + LVGL)

Target: **VIEWE UEDX48480021-MD80E** (480×480, ST7701S, knob + touch). See [`hardware-viewe.md`](hardware-viewe.md).

### Prep without hardware ✅

- [x] Shared serial protocol (`protocol.py` + `firmware/viewe/protocol.cpp`)
- [x] Fake serial device (`scripts/fake_serial_device.py`)
- [x] Firmware asset export (`scripts/export_firmware_assets.py`)
- [x] Arduino sketch skeleton (`firmware/viewe/cursor_agent_beacon/`)

### Needs the board

- [ ] Verify VIEWESMART `examples/2.1inch` compiles and runs
- [ ] Merge vendor LVGL + `ESP32_Display_Panel` init into beacon sketch
- [ ] Parse `STATUS|state|message` and switch LVGL animation
- [ ] Load PNG frames from `firmware/viewe/data/standard/`
- [ ] Optional caption line under character
- [ ] (Later) knob/button → `EVENT|...` serial lines

Assets: [`themes/standard/ASSETS.md`](../themes/standard/ASSETS.md) · export with `scripts/export_firmware_assets.py`

## Design notes

The original Spanish design document with hardware wiring and protocol details is preserved in [`design-notes.es.md`](design-notes.es.md).
