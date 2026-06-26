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
| `afterShellExecution` | `success` / `error` | Shell command |
| `beforeMCPExecution` | `running_mcp` | Tool: server:tool |
| `afterMCPExecution` | `success` | Tool done: ... |
| `afterAgentResponse` | `success` | Response preview |
| `stop` | `success` / `error` / `idle` | Ready / error / aborted |
| `preToolUse` | `waiting` | Using tool |
| `postToolUse` | `success` | Done: tool |
| `postToolUseFailure` | `error` | Failed: tool |
| `subagentStart` | `thinking` | Subagent: explore |
| `subagentStop` | `success` | Subagent finished |

Unsupported hooks are ignored safely.

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
3. Check stderr JSON lines and `.cursor-agent-beacon/status.json`

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
