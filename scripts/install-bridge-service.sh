#!/usr/bin/env bash
# Install systemd --user unit for the HTTP→serial bridge (no open terminal).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
UNIT_NAME="cursor-agent-beacon-bridge.service"
TEMPLATE="${ROOT}/packaging/${UNIT_NAME}"
USER_UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/cursor-agent-beacon"
ENV_FILE="${CONFIG_DIR}/bridge.env"
HARDWARE_ENV="${CURSOR_AGENT_BEACON_HARDWARE_ENV:-$ROOT/config/hardware.env}"

resolve_bin() {
  if [[ -n "${CURSOR_AGENT_BEACON_BIN:-}" && -x "${CURSOR_AGENT_BEACON_BIN}" ]]; then
    printf '%s\n' "${CURSOR_AGENT_BEACON_BIN}"
    return
  fi
  if [[ -x "${ROOT}/.venv/bin/cursor-agent-beacon" ]]; then
    printf '%s\n' "${ROOT}/.venv/bin/cursor-agent-beacon"
    return
  fi
  if command -v cursor-agent-beacon >/dev/null 2>&1; then
    command -v cursor-agent-beacon
    return
  fi
  echo "cursor-agent-beacon not found. Set CURSOR_AGENT_BEACON_BIN or create .venv." >&2
  exit 1
}

BEACON_BIN="$(resolve_bin)"
mkdir -p "${USER_UNIT_DIR}" "${CONFIG_DIR}"

if [[ -f "${HARDWARE_ENV}" ]]; then
  # Drop relative THEMES_DIR; package/editable install resolves themes.
  grep -v '^[[:space:]]*#' "${HARDWARE_ENV}" \
    | grep -v '^[[:space:]]*$' \
    | grep -v '^CURSOR_AGENT_BEACON_THEMES_DIR=' \
    > "${ENV_FILE}" || true
  # Absolute themes path if still needed (dev without packaged themes)
  if [[ -d "${ROOT}/themes" ]]; then
    echo "CURSOR_AGENT_BEACON_THEMES_DIR=${ROOT}/themes" >> "${ENV_FILE}"
  fi
  echo "CURSOR_AGENT_BEACON_STATUS_FILE=${HOME}/.local/share/cursor-agent-beacon/status.json" >> "${ENV_FILE}"
else
  cat > "${ENV_FILE}" <<EOF
CURSOR_AGENT_BEACON_SERIAL_PORT=/dev/ttyACM0
CURSOR_AGENT_BEACON_SERIAL_BAUD=115200
CURSOR_AGENT_BEACON_THEME=standard
CURSOR_AGENT_BEACON_BRIDGE_HOST=127.0.0.1
CURSOR_AGENT_BEACON_BRIDGE_PORT=8765
CURSOR_AGENT_BEACON_THEMES_DIR=${ROOT}/themes
CURSOR_AGENT_BEACON_STATUS_FILE=${HOME}/.local/share/cursor-agent-beacon/status.json
EOF
  echo "No ${HARDWARE_ENV}; wrote defaults to ${ENV_FILE}" >&2
fi

# Escape for systemd unit (no spaces expected in typical paths)
ESCAPED_BIN="${BEACON_BIN//\\/\\\\}"
ESCAPED_BIN="${ESCAPED_BIN//\"/\\\"}"

sed \
  -e "s|^ExecStart=.*|ExecStart=${ESCAPED_BIN} bridge|" \
  "${TEMPLATE}" > "${USER_UNIT_DIR}/${UNIT_NAME}"

systemctl --user daemon-reload
systemctl --user enable --now "${UNIT_NAME}"

echo "Installed ${USER_UNIT_DIR}/${UNIT_NAME}"
echo "Env:      ${ENV_FILE}"
echo "Binary:   ${BEACON_BIN}"
echo
systemctl --user --no-pager status "${UNIT_NAME}" || true
echo
echo "Useful:"
echo "  systemctl --user status ${UNIT_NAME}"
echo "  journalctl --user -u ${UNIT_NAME} -f"
echo "  systemctl --user restart ${UNIT_NAME}"
