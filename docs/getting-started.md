# Getting Started

## Prerequisites

- Python 3.10+
- [Cursor](https://cursor.com) with hooks enabled

## Install locally

```bash
git clone https://github.com/suribe06/cursor-agent-beacon.git
cd cursor-agent-beacon

python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Enable hooks

This repo includes project hooks:

- `.cursor/hooks.json`
- `.cursor/hooks/hook-handler.py`

Open the folder in Cursor. Hooks reload when the config is saved.

To use the beacon in another project, copy those two paths or install the package and point your hook command at the handler.

## Verify without Cursor (CLI)

Simulate hook stdin and check the handler response:

```bash
python3 scripts/simulate_hook.py examples/sample-events/before_shell_execution.json
python3 scripts/simulate_hook.py examples/sample-events/stop_completed.json
```

Inspect status mapping only:

```bash
PYTHONPATH=src python3 -m cursor_agent_beacon.cli map examples/sample-events/after_agent_thought.json
```

Run tests:

```bash
pytest
```

## End-to-end test in Cursor

1. Open this repository in Cursor (`File → Open Folder`).
2. Confirm `.cursor/hooks.json` exists at the project root.
3. Open **Output → Hooks** in the panel below the editor.
4. Start an Agent chat and send any prompt (triggers `beforeSubmitPrompt`, `afterAgentThought`, etc.).
5. Ask the agent to run a harmless shell command, e.g. `echo hello` (triggers `beforeShellExecution` / `afterShellExecution`).
6. Check the latest status file:

```bash
cat .cursor-agent-beacon/status.json
```

You should see JSON with `"state"`, `"message"`, and `"hook_event_name"` updating as the agent works.

Optional live watch:

```bash
watch -n 1 cat .cursor-agent-beacon/status.json
```

Structured hook logs also appear in the **Hooks** output channel (stderr JSON lines).

## Preview display theme

```bash
xdg-open preview/display-simulator.html
```

Toggle **Show exported GIF** to view bundled files from `themes/standard/assets/`.

Regenerate GIFs after editing sprites:

```bash
pip install Pillow
python3 scripts/export_standard_gifs.py
```

## Custom GIF theme

See [`themes/custom/README.md`](../themes/custom/README.md).

```bash
export CURSOR_AGENT_BEACON_THEME=your-theme-name
```

## Configuration

| Variable | Default | Description |
|---|---|---|
| `CURSOR_AGENT_BEACON_STATUS_FILE` | `.cursor-agent-beacon/status.json` | Latest status path |
| `CURSOR_AGENT_BEACON_THEME` | `standard` | Theme id |
| `CURSOR_AGENT_BEACON_THEMES_DIR` | `themes` | Theme packs root |
| `CURSOR_AGENT_BEACON_HTTP_URL` | unset | Bridge endpoint (Phase 2) |

## Next steps

- [Hooks Reference](hooks.md)
- [Display themes](display-themes.md)
- [Architecture](architecture.md)
- [Roadmap](roadmap.md) — bridge, ESP32, MCP
