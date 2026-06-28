#!/usr/bin/env bash
# Install global hooks + GNOME top-bar panel (Ubuntu).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
"${ROOT}/scripts/install-user-hooks.sh"
"${ROOT}/scripts/install-gnome-panel.sh"
