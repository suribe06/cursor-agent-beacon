#!/usr/bin/env bash
# Install global hooks + GNOME top-bar panel (Ubuntu).
set -euo pipefail

if command -v cursor-agent-beacon >/dev/null 2>&1; then
  exec cursor-agent-beacon install-desktop
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"
exec python3 -m cursor_agent_beacon.cli install-desktop
