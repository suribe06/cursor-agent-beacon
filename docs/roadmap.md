# Roadmap

## Phase 1 — Python hooks ✅

- [x] Normalize Cursor hook events into agent status
- [x] Pluggable sinks (log, file, HTTP stub)
- [x] Project-level `.cursor/hooks.json`
- [x] Local simulation script and tests

## Phase 1.5 — Standard display theme ✅

- [x] Pixel robot sprite generator (`scripts/build_character_sprites.py`)
- [x] Export 240×240 GIFs (`scripts/export_standard_gifs.py`)
- [x] `themes/standard/manifest.json` + bundled assets
- [x] Custom theme layout (`themes/custom/`)
- [x] Theme loader (`cursor_agent_beacon.theme`)
- [x] Browser preview (`preview/display-simulator.html`)

## Phase 2 — Local bridge service

- [ ] Long-running Python service
- [ ] `POST /status` endpoint for hook handler
- [ ] Resolve GIF from theme pack per agent state
- [ ] Serial writer thread for ESP32 commands
- [ ] Single owner of the USB serial port

## Phase 3 — ESP32 display firmware

- [ ] ESP32 + ST7789/GC9A01 240×240 color TFT
- [ ] GIF playback from SPIFFS/SD using `themes/standard/manifest.json`
- [ ] Parse `STATUS|state|message` serial lines
- [ ] Debounced button on D2 with `INPUT_PULLUP`
- [ ] Emit `EVENT|button_pressed` on serial
- [ ] Optional caption line under character

Assets ready: [`themes/standard/ASSETS.md`](../themes/standard/ASSETS.md)

## Phase 4 — MCP input path

- [ ] FastMCP server exposing `get_pending_events`
- [ ] Background serial reader for button events
- [ ] Project rule prompting the agent to poll pending events

## Design notes

The original Spanish design document with hardware wiring and protocol details is preserved in [`design-notes.es.md`](design-notes.es.md).
