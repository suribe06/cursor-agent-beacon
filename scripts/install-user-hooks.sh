#!/usr/bin/env bash
# Install user-level Cursor hooks → cursor-agent-beacon (global status dir).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOOK_HANDLER="${ROOT}/.cursor/hooks/hook-handler.py"
CURSOR_DIR="${HOME}/.cursor"
HOOKS_DIR="${CURSOR_DIR}/hooks"
WRAPPER="${HOOKS_DIR}/cursor-agent-beacon.sh"
STATUS_DIR="${HOME}/.local/share/cursor-agent-beacon"
STATUS_FILE="${STATUS_DIR}/status.json"

if [[ ! -f "$HOOK_HANDLER" ]]; then
  echo "hook-handler not found: $HOOK_HANDLER" >&2
  exit 1
fi

mkdir -p "$HOOKS_DIR" "$STATUS_DIR"

cat > "$WRAPPER" <<EOF
#!/usr/bin/env bash
export CURSOR_AGENT_BEACON_STATUS_FILE="${STATUS_FILE}"
exec python3 "${HOOK_HANDLER}" "\$@"
EOF
chmod +x "$WRAPPER"

# ponytail: overwrites ~/.cursor/hooks.json — merge manually if you have other hooks
cat > "${CURSOR_DIR}/hooks.json" <<'EOF'
{
  "version": 1,
  "hooks": {
    "sessionStart": [{ "command": "./hooks/cursor-agent-beacon.sh", "timeout": 5 }],
    "sessionEnd": [{ "command": "./hooks/cursor-agent-beacon.sh", "timeout": 5 }],
    "beforeSubmitPrompt": [{ "command": "./hooks/cursor-agent-beacon.sh", "timeout": 5 }],
    "afterAgentThought": [{ "command": "./hooks/cursor-agent-beacon.sh", "timeout": 5 }],
    "beforeShellExecution": [{ "command": "./hooks/cursor-agent-beacon.sh", "timeout": 5 }],
    "afterShellExecution": [{ "command": "./hooks/cursor-agent-beacon.sh", "timeout": 5 }],
    "beforeMCPExecution": [{ "command": "./hooks/cursor-agent-beacon.sh", "timeout": 5 }],
    "afterMCPExecution": [{ "command": "./hooks/cursor-agent-beacon.sh", "timeout": 5 }],
    "afterAgentResponse": [{ "command": "./hooks/cursor-agent-beacon.sh", "timeout": 5 }],
    "stop": [{ "command": "./hooks/cursor-agent-beacon.sh", "timeout": 5 }],
    "preToolUse": [{ "command": "./hooks/cursor-agent-beacon.sh", "timeout": 5 }],
    "postToolUse": [{ "command": "./hooks/cursor-agent-beacon.sh", "timeout": 5 }],
    "postToolUseFailure": [{ "command": "./hooks/cursor-agent-beacon.sh", "timeout": 5 }],
    "subagentStart": [{ "command": "./hooks/cursor-agent-beacon.sh", "timeout": 5 }],
    "subagentStop": [{ "command": "./hooks/cursor-agent-beacon.sh", "timeout": 5 }]
  }
}
EOF

echo "Hooks: ${CURSOR_DIR}/hooks.json"
echo "Wrapper: $WRAPPER"
echo "Status: ${STATUS_DIR}/ (registry.json + sessions/)"
echo "Restart Cursor after install."
