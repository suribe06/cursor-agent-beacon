#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BEACON="${ROOT}/.venv/bin/cursor-agent-beacon"
if [[ ! -x "${BEACON}" ]]; then
  echo "Run ./setup.sh first (creates .venv and installs the package)." >&2
  exit 1
fi
exec "${BEACON}" install-gnome
