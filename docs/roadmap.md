# Roadmap

Living checklist against the current tree. Shipped items match code in `main` / the latest release; open items live under [Future work](#future-work) too when they are exploratory.

## Phase 1 — Python hooks ✅

- [x] Normalize Cursor hook events into agent status
- [x] Pluggable sinks (log, file, HTTP)
- [x] Project-level `.cursor/hooks.json`
- [x] Local simulation script and tests
- [x] User install path: `setup` / `doctor` / `status` / `uninstall` + PyPI package

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
- [x] Systemd user unit (`scripts/install-bridge-service.sh`)

## Phase 2.5 — GNOME desktop panel ✅

Target: Ubuntu / GNOME Shell 46+ top-bar indicator.

- [x] Multi-session registry on disk (`~/.local/share/cursor-agent-beacon/`)
- [x] GNOME Shell extension (`gnome-extension/`)
- [x] User-level hook installer (`scripts/install-user-hooks.sh` / `setup`)
- [x] Session pin menu + human-readable timestamps
- [x] Turn timer (`started_at`) in panel
- [x] Model / effort / attachments / context in the popup menu
- [x] Context `%` badge in the top bar (honors `display.toml`)
- [ ] Stable panel position across shell restarts → [Future work](#future-work)

Install: `./scripts/install-desktop.sh` or `cursor-agent-beacon setup` · Docs: [`gnome-panel.md`](gnome-panel.md)

## Phase 3 — VIEWE display firmware (ESP32-S3 + LVGL) ✅

Target: **VIEWE UEDX48480021-MD80ET** (480×480, ST7701S). Docs: [`hardware-viewe.md`](hardware-viewe.md) · hub: [`hardware.md`](hardware.md).

### Prep without hardware ✅

- [x] Shared serial protocol (`protocol.py` + `firmware/viewe/protocol.cpp`)
- [x] Fake serial device (`scripts/fake_serial_device.py`)
- [x] Firmware asset export (`scripts/export_firmware_assets.py`)
- [x] Arduino sketch skeleton (`firmware/viewe/cursor_agent_beacon/`)

### On the board ✅

- [x] Verify VIEWESMART board / flash path (MD80ET + USB CDC)
- [x] Merge vendor LVGL + `ESP32_Display_Panel` init into beacon sketch
- [x] Parse `STATUS|state|message[|model[|ctx_pct]]` and update UI
- [x] Embed standard GIFs + `LV_USE_GIF` (`scripts/embed_theme_gifs.py`)
- [x] Meter Band layout: state + message + model line + labeled context bar
- [x] Systemd user bridge (`scripts/install-bridge-service.sh`)
- [x] Parametric stand SCAD (`hardware/case/viewe-2.1/`)
- [ ] Knob/button → `EVENT|...` serial lines → [Future work](#future-work)
- [ ] FFat theme swap without reflash → [Future work](#future-work)

Assets: [`themes/standard/ASSETS.md`](../themes/standard/ASSETS.md) · embed with `scripts/embed_theme_gifs.py`

## Phase 4 — Rich status + display prefs ✅

Shipped across **v0.5.0**–**v0.5.2**.

- [x] Sticky raw model slug + effort (skip Cursor `default` placeholder)
- [x] Prompt attachment summary on status
- [x] Context usage from `preCompact` + sticky fields on the serial line (`ctx_pct`)
- [x] Transcript-based context **estimate** between rare `preCompact` hooks (`context_estimate.py`)
- [x] `~/.config/cursor-agent-beacon/display.toml` shared `[show]` toggles + `extension.panel_badge`
- [x] `setup` creates `display.toml` once (never overwrites edits)
- [x] `cursor-agent-beacon reload` applies prefs and pushes the bridge

Docs: [`getting-started.md`](getting-started.md#display-preferences) · env: `CURSOR_AGENT_BEACON_DISPLAY_CONFIG`

## Design notes

The original Spanish design document with hardware wiring and protocol details is preserved in [`design-notes.es.md`](design-notes.es.md).

## Future work

Open directions — not committed for a near release. Order is preference, not schedule.

### Display preferences

- **Auto-reload `display.toml`** — watch the config file (inotify / polling) and apply prefs without running `cursor-agent-beacon reload`. Manual reload stays as the explicit fallback.
- **Per-surface overrides** — optional `[display]` / `[extension]` sections if shared `[show]` proves too coarse.
- **`cursor-agent-beacon prefs`** — tiny CLI to get/set toggles without editing TOML by hand.

### Context usage

- **Better transcript calibration** — learn bytes/token continuously; reduce drift vs Cursor’s Context Usage UI.
- **Post-compact refresh** — after compaction, prefer a fresh estimate (or a future Cursor hook) over a sticky preCompact peak.
- **Optional Cursor-internal probe** — only if a stable, documented source appears; avoid scraping private IDE state.

### Hardware (VIEWE)

- Knob / button → `EVENT|...` serial lines (ack, pin session, mute).
- FFat / SD theme swap without reflash.
- Arc or radial context meter (round-native Meter Band variant).
- Multi-line model slug truncation rules for long Cursor model ids.

### Desktop / multi-session

- Stable GNOME panel position across Shell restarts.
- Richer multi-window focus when several Cursor windows are open.
- Optional notification on error / long-running shell.

### Platform

- macOS menu-bar companion (parity with GNOME panel).
- Windows tray companion.
- Packaged firmware flash from `cursor-agent-beacon` CLI (wrap `flash-viewe.sh`).
