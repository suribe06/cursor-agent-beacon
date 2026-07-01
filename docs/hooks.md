# Hooks Reference

Cursor sends JSON on stdin for every hook invocation. Cursor Agent Beacon maps supported hooks to normalized status updates.

Official Cursor docs: https://cursor.com/docs/hooks

## Supported hooks

| Hook | Mapped state | Example message |
| --- | --- | --- |
| `sessionStart` | `idle` | Session started |
| `sessionEnd` | `idle` | Session ended |
| `beforeSubmitPrompt` | `waiting` | First line of prompt |
| `afterAgentThought` | `thinking` | Thinking... |
| `beforeShellExecution` | `running_shell` | Shell command |
| `afterShellExecution` | `thinking` / `error` | Shell done / failed |
| `beforeMCPExecution` | `running_mcp` | Tool: server:tool |
| `afterMCPExecution` | `thinking` | Thinking... |
| `afterAgentResponse` | `thinking` | Response preview |
| `stop` | `success` / `error` / `idle` | Ready / error / aborted |
| `preToolUse` | `waiting` | Using tool |
| `postToolUse` | `thinking` | Thinking... |
| `postToolUseFailure` | `error` / `waiting` | Failed: tool / Denied: tool (user rejected) |
| `subagentStart` | `thinking` | Subagent: explore |
| `subagentStop` | `thinking` | Thinking... |
| `beforeReadFile` | `thinking` | Reading file... |
| `afterFileEdit` | `thinking` | Editing file... |
| `preCompact` | `thinking` | Compacting context... |

Unsupported hooks are ignored safely.

## Multi-session status files

When `CURSOR_AGENT_BEACON_STATUS_FILE` points at `~/.local/share/cursor-agent-beacon/status.json` (default after `./scripts/install-user-hooks.sh`), the file sink also writes:

| Path | Purpose |
| --- | --- |
| `registry.json` | Index of active sessions + `focused_conversation_id` |
| `sessions/<conversation_id>.json` | Per-chat state, label, project |
| `status.json` | Auto-focused session snapshot (GNOME panel reads this + registry) |

## Global vs project hooks

| Setup | Hooks location | Status dir |
| --- | --- | --- |
| Open repo in Cursor | `.cursor/hooks.json` (project) | `.cursor-agent-beacon/` (project) |
| `./scripts/install-user-hooks.sh` | `~/.cursor/hooks.json` (user) | `~/.local/share/cursor-agent-beacon/` |

Use **user hooks** for the GNOME panel across all projects.

## Hook responses

The handler returns permissive responses so Cursor never gets blocked:

| Hook family | Response |
| --- | --- |
| `beforeShellExecution`, `beforeMCPExecution`, `subagentStart` | `{"permission":"allow"}` |
| `beforeSubmitPrompt` | `{"continue":true}` |
| Observability hooks | `{}` |

## Sample payloads

See [`examples/sample-events/`](../examples/sample-events/).

## Debugging

1. Open Cursor → Output → **Hooks**
2. Trigger an agent action (shell command, MCP call, response)
3. Check stderr JSON lines and status files:

```bash
# project hooks
cat .cursor-agent-beacon/status.json

# user hooks (GNOME panel)
cat ~/.local/share/cursor-agent-beacon/status.json
cat ~/.local/share/cursor-agent-beacon/registry.json
```

If hooks do not load:

- confirm `.cursor/hooks.json` paths are relative to the project root
- restart Cursor
- verify `python3` is available to the hook process

## Customization

Mapping logic lives in `src/cursor_agent_beacon/mapper.py`.

Add sinks in `src/cursor_agent_beacon/sinks/` and register them in `build_sinks()`.

For the VIEWE bridge, set:

```bash
export CURSOR_AGENT_BEACON_HTTP_URL=http://127.0.0.1:8765/status
```

The HTTP sink POSTs:

```json
{
  "state": "running_shell",
  "message": "npm test",
  "hook_event_name": "beforeShellExecution",
  "conversation_id": "...",
  "timestamp": "..."
}
```
