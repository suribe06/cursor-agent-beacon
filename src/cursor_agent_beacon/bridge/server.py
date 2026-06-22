"""HTTP server exposing POST /status for the hook handler."""

from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cursor_agent_beacon.bridge.service import BridgeService


def run_bridge_server(service: BridgeService, host: str, port: int) -> None:
    handler = _make_handler(service)
    server = ThreadingHTTPServer((host, port), handler)
    server.daemon_threads = True

    print(
        f"[cursor-agent-beacon-bridge] listening on http://{host}:{port}",
        file=sys.stderr,
        flush=True,
    )
    print(
        f"[cursor-agent-beacon-bridge] POST status to {service.config.status_url}",
        file=sys.stderr,
        flush=True,
    )
    if service.config.serial_port:
        print(
            f"[cursor-agent-beacon-bridge] serial port {service.config.serial_port} "
            f"@ {service.config.serial_baud} baud",
            file=sys.stderr,
            flush=True,
        )
    else:
        print(
            "[cursor-agent-beacon-bridge] serial dry-run (set "
            "CURSOR_AGENT_BEACON_SERIAL_PORT to enable hardware)",
            file=sys.stderr,
            flush=True,
        )

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print(
            "\n[cursor-agent-beacon-bridge] shutting down",
            file=sys.stderr,
            flush=True,
        )
    finally:
        server.shutdown()
        server.server_close()
        service.close()


def _make_handler(service: BridgeService) -> type[BaseHTTPRequestHandler]:
    class BridgeHTTPRequestHandler(BaseHTTPRequestHandler):
        server_version = "CursorAgentBeaconBridge/0.2"

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            print(
                f"[cursor-agent-beacon-bridge] {self.address_string()} - "
                f"{format % args}",
                file=sys.stderr,
                flush=True,
            )

        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/health":
                self._json_response(200, service.health())
                return
            if self.path == "/status":
                latest = service.latest_status
                if latest is None:
                    self._json_response(404, {"ok": False, "error": "no status yet"})
                    return
                self._json_response(200, {"ok": True, "status": latest.to_dict()})
                return
            self._json_response(404, {"ok": False, "error": "not found"})

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/status":
                self._json_response(404, {"ok": False, "error": "not found"})
                return

            length_raw = self.headers.get("Content-Length", "0")
            try:
                length = int(length_raw)
            except ValueError:
                self._json_response(
                    400,
                    {"ok": False, "error": "invalid Content-Length"},
                )
                return

            raw = self.rfile.read(length)
            try:
                payload = json.loads(raw.decode("utf-8") or "{}")
            except json.JSONDecodeError:
                self._json_response(400, {"ok": False, "error": "invalid JSON"})
                return

            if "state" not in payload:
                self._json_response(400, {"ok": False, "error": "missing state"})
                return

            try:
                result = service.handle_status(payload)
            except ValueError as exc:
                self._json_response(400, {"ok": False, "error": str(exc)})
                return
            except Exception as exc:  # noqa: BLE001
                self._json_response(500, {"ok": False, "error": str(exc)})
                return

            self._json_response(200, result)

        def _json_response(self, code: int, payload: dict) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return BridgeHTTPRequestHandler
