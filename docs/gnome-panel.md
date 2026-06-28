# GNOME Status Panel

Pre-release (**v0.10**) GNOME Shell extension that reads multi-session status from cursor-agent-beacon.

## Requirements

- Ubuntu / GNOME Shell 46+
- User-level hooks installed (see below)

## Install

From the repo root:

```bash
./scripts/install-desktop.sh
```

Or step by step:

```bash
./scripts/install-user-hooks.sh   # ~/.cursor/hooks.json + global status dir
./scripts/install-gnome-panel.sh  # GNOME extension
```

Then restart Cursor and GNOME Shell (`Alt+F2` → `r` on X11).

## Data flow

```text
Cursor hooks → ~/.local/share/cursor-agent-beacon/
                 registry.json
                 sessions/<id>.json
                 status.json
                      ↓ poll
               GNOME panel (gnome-extension/)
```

## Panel features

- Shows busiest session by default; badge when multiple agents are active
- Menu lists active sessions; click to **pin** (★)
- Human-readable timestamps (`2m ago`, not ISO)
- Optional panel side: `gsettings set org.gnome.shell.extensions.cursor-status-panel panel-side left`

## Source

Extension lives in [`gnome-extension/`](../gnome-extension/).
