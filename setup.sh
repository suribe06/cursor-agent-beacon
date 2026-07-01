#!/usr/bin/env bash
# End-user setup: venv → pip install → global hooks (+ GNOME panel on Ubuntu).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if ! python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'; then
  echo "cursor-agent-beacon requires Python 3.10 or newer." >&2
  exit 1
fi

if [[ ! -d .venv ]]; then
  echo "Creating .venv..."
  python3 -m venv .venv
fi

echo "Installing cursor-agent-beacon..."
.venv/bin/pip install -q -U pip
.venv/bin/pip install -q -e ".[bridge]"

BEACON_BIN="${ROOT}/.venv/bin/cursor-agent-beacon"
exec "${BEACON_BIN}" setup --beacon-bin "${BEACON_BIN}" "$@"
