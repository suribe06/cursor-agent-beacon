# Architecture

Cursor Agent Beacon turns native Cursor hook events into normalized agent status updates, with bundled GIF themes for a future physical display.

## Why hooks?

Cursor hooks fire deterministically during the agent lifecycle. They do not depend on the model choosing to report status. That makes them ideal for physical panels, dashboards, logging, and automation.

## Current scope (v0.1)

| Layer | Status |
|---|---|
| Python hook handler | ✅ Shipped |
| Status sinks (log, file, HTTP stub) | ✅ Shipped |
| Standard GIF theme (240×240) | ✅ Bundled in repo |
| Custom theme packs | ✅ Layout + loader |
| Local bridge service | 🔜 Phase 2 |
| ESP32 firmware | 🔜 Phase 3 |
| MCP button input | 🔜 Phase 4 |

## Data flow (today)

```text
Cursor agent lifecycle
        │
        ▼
.cursor/hooks.json
        │
        ▼
hook-handler.py (stdin JSON)
        │
        ▼
cursor_agent_beacon.handler
        │
        ├── mapper.py      → AgentStatus
        ├── theme.py       → GIF path (for bridge/firmware)
        └── sinks/         → stderr, file, HTTP (bridge stub)
```

## Data flow (target)

```text
Hooks → HTTP POST → bridge service → serial → ESP32 → GIF + caption
                                                      ↑
Button ── serial EVENT ── MCP get_pending_events ────┘
```

## Normalized status

Each hook produces an `AgentStatus` object:

| Field | Description |
| --- | --- |
| `state` | `idle`, `waiting`, `thinking`, `running_shell`, `running_mcp`, `success`, `error` |
| `message` | Short human-readable summary |
| `hook_event_name` | Original Cursor hook name |
| `conversation_id` | Cursor conversation id when available |
| `timestamp` | UTC ISO-8601 timestamp |

Serial format for the bridge (planned):

```text
STATUS|<state>|<message>
THEME|<theme_id>
```

## Theme packs

Standard theme maps each agent state to a GIF in `themes/standard/assets/`. See [Display themes](display-themes.md).

Custom themes live under `themes/custom/<name>/` (gitignored).

## Failure behavior

Hooks must never block Cursor. The handler:

- catches all exceptions
- logs errors to stderr
- returns a permissive JSON response (`continue: true` / `permission: allow`)
- exits with code `0`

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `CURSOR_AGENT_BEACON_LOG` | `true` | Write JSON lines to stderr |
| `CURSOR_AGENT_BEACON_FILE` | `true` | Persist latest status to disk |
| `CURSOR_AGENT_BEACON_STATUS_FILE` | `.cursor-agent-beacon/status.json` | Status snapshot path |
| `CURSOR_AGENT_BEACON_HTTP_URL` | unset | POST status to local bridge |
| `CURSOR_AGENT_BEACON_HTTP_TIMEOUT` | `1.0` | HTTP timeout in seconds |
| `CURSOR_AGENT_BEACON_THEME` | `standard` | Active theme id |
| `CURSOR_AGENT_BEACON_THEMES_DIR` | `themes` | Theme packs root |

## Project layout

```text
src/cursor_agent_beacon/   Python package
themes/standard/           Bundled GIF theme
themes/custom/             Personal themes (gitignored)
.cursor/hooks/             Cursor hook entry point
preview/                   Display simulator
scripts/                   Sprite export + hook simulation
tests/                     Unit tests
docs/                      Documentation
```

See also:

- [Getting Started](getting-started.md)
- [Hooks Reference](hooks.md)
- [Display themes](display-themes.md)
- [Roadmap](roadmap.md)
