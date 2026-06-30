"""Additional bridge server tests."""

from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

from cursor_agent_beacon.bridge.config import BridgeConfig
from cursor_agent_beacon.bridge.serial_writer import DryRunSerialWriter
from cursor_agent_beacon.bridge.server import run_bridge_server
from cursor_agent_beacon.bridge.service import BridgeService
from cursor_agent_beacon.theme import load_theme


def _write_theme(tmp_path: Path) -> Path:
    theme_root = tmp_path / "standard"
    assets = theme_root / "assets"
    assets.mkdir(parents=True)
    (assets / "thinking.gif").write_bytes(b"GIF")
    manifest = {
        "id": "standard",
        "name": "Test",
        "states": {
            "thinking": {
                "animation": "assets/thinking.gif",
                "loop": True,
                "caption": "Thinking",
            }
        },
    }
    (theme_root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return tmp_path


def _wait_for_server(url: str, attempts: int = 50) -> None:
    for _ in range(attempts):
        try:
            with urllib.request.urlopen(url, timeout=0.2):
                return
        except (urllib.error.URLError, TimeoutError, OSError):
            time.sleep(0.05)
    raise RuntimeError("bridge server did not start")


def test_bridge_rejects_oversized_body(tmp_path: Path):
    themes_root = _write_theme(tmp_path)
    config = BridgeConfig(host="127.0.0.1", port=18766, themes_dir=themes_root)
    service = BridgeService(
        config,
        theme=load_theme("standard", themes_root),
        serial_writer=DryRunSerialWriter(),
    )
    thread = threading.Thread(
        target=run_bridge_server,
        args=(service, config.host, config.port),
        daemon=True,
    )
    thread.start()
    _wait_for_server(f"http://{config.host}:{config.port}/health")

    huge = b"x" * (64 * 1024 + 1)
    request = urllib.request.Request(
        f"http://{config.host}:{config.port}/status",
        data=huge,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        urllib.request.urlopen(request, timeout=2.0)
        raised = False
    except urllib.error.HTTPError as exc:
        raised = True
        assert exc.code == 413
        body = json.loads(exc.read().decode("utf-8"))
        assert body["ok"] is False

    assert raised
    service.close()
