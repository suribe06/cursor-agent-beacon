#!/usr/bin/env bash
# Install the local GNOME panel and open a nested Shell to preview changes
# without logging out of the host Wayland session.
#
# Usage (from repo root):
#   ./scripts/dev-gnome-panel.sh
#
# First time on Ubuntu 26.04 / GNOME 49+:
#   sudo apt install mutter-dev-bin
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UUID="cursor-status-panel@suribe06"
BEACON="${ROOT}/.venv/bin/cursor-agent-beacon"

if [[ ! -x "${BEACON}" ]]; then
  echo "Missing ${BEACON} — run: python3 -m venv .venv && .venv/bin/pip install -e ." >&2
  exit 1
fi

"${BEACON}" install-gnome

SESSION_TYPE="${XDG_SESSION_TYPE:-}"
echo "Installed ${UUID} from ${ROOT}/gnome-extension"
echo "Session: ${SESSION_TYPE:-unknown}"
echo

if [[ "${SESSION_TYPE}" == "x11" ]]; then
  echo "X11: press Alt+F2, type  r  , Enter — that restarts GNOME Shell and reloads extensions."
  echo "Then: gnome-extensions enable ${UUID}"
  exit 0
fi

if ! gnome-shell --help 2>&1 | grep -q -- '--devkit'; then
  echo "This gnome-shell has no --devkit; use logout/login after install-gnome." >&2
  exit 1
fi

if [[ ! -x /usr/libexec/mutter-devkit ]] && ! command -v mutter-devkit >/dev/null 2>&1; then
  echo "mutter-devkit not found. On Ubuntu:" >&2
  echo "  sudo apt install mutter-dev-bin" >&2
  exit 1
fi

echo "Wayland: launching a nested GNOME Shell (devkit)."
echo "Inside that window, open a terminal and run:"
echo "  gnome-extensions enable ${UUID}"
echo "Close the nested window when done — your main session stays up."
echo

exec dbus-run-session -- gnome-shell --devkit --wayland
