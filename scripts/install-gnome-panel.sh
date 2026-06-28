#!/usr/bin/env bash
set -euo pipefail

UUID="cursor-status-panel@suribe06"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="${ROOT}/gnome-extension"
DEST="${HOME}/.local/share/gnome-shell/extensions/${UUID}"

rm -rf "$DEST"
mkdir -p "$DEST"
cp "${SRC}/extension.js" "${SRC}/metadata.json" "${SRC}/stylesheet.css" "$DEST/"
cp -r "${SRC}/schemas" "$DEST/"
glib-compile-schemas "${DEST}/schemas/"

gnome-extensions disable "$UUID" 2>/dev/null || true
gnome-extensions enable "$UUID" 2>/dev/null || true

echo "Installed to $DEST"
echo "Restart GNOME Shell if the panel does not update: Alt+F2 → r (X11) or log out (Wayland)."
