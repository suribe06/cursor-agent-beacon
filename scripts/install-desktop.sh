#!/usr/bin/env bash
# Install global hooks + GNOME top-bar panel (Ubuntu).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec "${ROOT}/setup.sh" "$@"
