# Hardware displays

Cursor Agent Beacon can drive a **physical status panel** over USB serial. The PC side (hooks → HTTP bridge → `STATUS|state|message`) is the same for every display. Only the **firmware** is board-specific.

## Supported today

| Display | Firmware | Setup guide |
| --- | --- | --- |
| **VIEWE UEDX48480021** (2.1″ 480×480; firmware uses `MD80ET` board macro) | [`firmware/viewe/`](../firmware/viewe/README.md) | [VIEWE setup](hardware-viewe.md) |

Only this family has in-repo flash scripts and tested LVGL + GIF firmware. Store labels may say **MD80E** or **MD80ET** — see [Which SKU?](hardware-viewe.md#which-sku-md80e-vs-md80et).

## Software stack (all displays)

```text
Cursor hooks → POST http://127.0.0.1:8765/status → bridge → USB serial
                                                         ↓
                                              your firmware UI
```

| Piece | Role |
| --- | --- |
| Hooks + HTTP sink | Already installed via `cursor-agent-beacon setup` |
| `cursor-agent-beacon bridge` | Single owner of the serial port; systemd: `./scripts/install-bridge-service.sh` |
| `config/hardware.env` | `SERIAL_PORT`, `HTTP_URL`, theme |
| Serial protocol | `STATUS\|state\|message` and `THEME\|id` @ **115200** (USB-CDC) |

Protocol details: [`src/cursor_agent_beacon/protocol.py`](../src/cursor_agent_beacon/protocol.py) and the C++ twin under `firmware/viewe/`.

## Other displays (bring-up guide)

You do **not** need a VIEWE to use the bridge. Any MCU that speaks the text protocol can show agent status.

1. **Keep the PC path** — hooks, `HTTP_URL`, and `cursor-agent-beacon bridge` with your `CURSOR_AGENT_BEACON_SERIAL_PORT`.
2. **Implement firmware** that:
   - Opens USB-CDC (or UART) at 115200
   - Parses lines `STATUS|<state>|<message>` (see `firmware/viewe/cursor_agent_beacon/protocol.*`)
   - Maps `state` → your UI (`idle`, `waiting`, `thinking`, `running_shell`, `running_mcp`, `success`, `error`, and optionally `stop`)
3. **Optional:** ignore `THEME|...` until you support theme packs on-device.
4. **Assets:** the bundled theme GIFs are **480×480** for the VIEWE. For another resolution, export or resize your own pack under `themes/custom/<name>/` and set `CURSOR_AGENT_BEACON_THEME`.
5. **Reference:** copy the VIEWE sketch’s serial loop + protocol parser; replace only the board/LVGL init and drawing code.

Suggested layout for a new board:

```text
firmware/<vendor-or-board>/
  README.md                 # flash FQBN, port, wiring
  <sketch>/                 # Arduino or ESP-IDF project
```

Open a PR with that folder + a row in the table above when it works on real hardware.

## Related

- [VIEWE setup](hardware-viewe.md)
- [Display themes](display-themes.md)
- [Getting Started](getting-started.md) (bridge without hardware)
- [Architecture](architecture.md)
