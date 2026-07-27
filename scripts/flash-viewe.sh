#!/usr/bin/env bash
# Compile + upload VIEWE UEDX48480021-MD80E beacon firmware via arduino-cli.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SKETCH="${ROOT}/firmware/viewe/cursor_agent_beacon"
PORT="${CURSOR_AGENT_BEACON_SERIAL_PORT:-/dev/ttyACM0}"

FQBN="${ARDUINO_FQBN:-esp32:esp32:esp32s3:UploadSpeed=921600,USBMode=hwcdc,CDCOnBoot=cdc,FlashMode=qio,FlashSize=16M,PartitionScheme=app3M_fat9M_16MB,PSRAM=opi,DebugLevel=info,EraseFlash=all}"

if ! command -v arduino-cli >/dev/null 2>&1; then
  echo "arduino-cli not found. Install: https://arduino.github.io/arduino-cli/" >&2
  exit 1
fi

if [[ ! -e "${PORT}" ]]; then
  echo "Serial port not found: ${PORT}" >&2
  echo "Connect the panel (USB-A data cable) and check: ls /dev/ttyACM*" >&2
  exit 1
fi

echo "Embedding theme GIFs ..."
python3 "${ROOT}/scripts/embed_theme_gifs.py"

echo "Compiling ${SKETCH} ..."
arduino-cli compile --fqbn "${FQBN}" "${SKETCH}"

echo "Uploading to ${PORT} ..."
arduino-cli upload -p "${PORT}" --fqbn "${FQBN}" "${SKETCH}"

echo "Done. Panel should show the idle GIF (sleeping robot)."
echo "Then: set -a && source config/hardware.env && set +a && cursor-agent-beacon bridge"
