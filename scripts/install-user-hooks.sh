#!/usr/bin/env bash
# Install user-level Cursor hooks → cursor-agent-beacon (global status dir).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec "${ROOT}/setup.sh" --hooks-only "$@"
