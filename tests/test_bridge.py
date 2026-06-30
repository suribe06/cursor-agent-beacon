"""Tests for the local bridge service."""

from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request
from io import StringIO
from pathlib import Path

import pytest

from cursor_agent_beacon.bridge.config import BridgeConfig, default_bridge_url
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


def test_default_bridge_url():
    assert default_bridge_url() == "http://127.0.0.1:8765/status"


def test_bridge_service_resolves_gif_and_serial(tmp_path: Path):
    themes_root = _write_theme(tmp_path)
    config = BridgeConfig(theme_id="standard", themes_dir=themes_root)
    serial = DryRunSerialWriter()
    stderr = StringIO()
    serial.write_line = lambda line: stderr.write(f"{line}\n")  # type: ignore[method-assign]

    service = BridgeService(
        config,
        theme=load_theme("standard", themes_root),
        serial_writer=serial,
    )

    result = service.handle_status(
        {
            "state": "thinking",
            "message": "Planning",
            "hook_event_name": "afterAgentThought",
        }
    )

    assert result["ok"] is True
    assert result["serial"] == "STATUS|thinking|Planning"
    assert result["gif"] == "assets/thinking.gif"
    assert result["caption"] == "Thinking"
    assert "THEME|standard" in stderr.getvalue()
    assert "STATUS|thinking|Planning" in stderr.getvalue()
    service.close()


def test_bridge_service_rejects_unknown_state(tmp_path: Path):
    themes_root = _write_theme(tmp_path)
    config = BridgeConfig(theme_id="standard", themes_dir=themes_root)
    service = BridgeService(
        config,
        theme=load_theme("standard", themes_root),
        serial_writer=DryRunSerialWriter(),
    )

    with pytest.raises(ValueError):
        service.handle_status({"state": "not-a-state", "message": "x"})
    service.close()


def test_bridge_http_post_status(tmp_path: Path):
    themes_root = _write_theme(tmp_path)
    config = BridgeConfig(host="127.0.0.1", port=18765, themes_dir=themes_root)
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

    payload = json.dumps(
        {
            "state": "thinking",
            "message": "Via HTTP",
            "hook_event_name": "afterAgentThought",
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"http://{config.host}:{config.port}/status",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=2.0) as response:
        body = json.loads(response.read().decode("utf-8"))

    assert body["ok"] is True
    assert body["gif"] == "assets/thinking.gif"
    assert body["serial"] == "STATUS|thinking|Via HTTP"

    health_request = urllib.request.Request(
        f"http://{config.host}:{config.port}/health",
        method="GET",
    )
    with urllib.request.urlopen(health_request, timeout=2.0) as response:
        health = json.loads(response.read().decode("utf-8"))

    assert health["ok"] is True
    assert health["latest"]["state"] == "thinking"
    service.close()


def test_bridge_service_stop_hook_prefers_stop_gif(tmp_path: Path):
    themes_root = tmp_path / "themes"
    theme_root = themes_root / "standard"
    assets = theme_root / "assets"
    assets.mkdir(parents=True)
    (assets / "success.gif").write_bytes(b"GIF")
    (assets / "stop.gif").write_bytes(b"GIF2")
    manifest = {
        "id": "standard",
        "name": "Test",
        "states": {
            "success": {"animation": "assets/success.gif", "loop": True},
            "stop": {"animation": "assets/stop.gif", "loop": False},
        },
    }
    (theme_root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    config = BridgeConfig(theme_id="standard", themes_dir=themes_root)
    service = BridgeService(
        config,
        theme=load_theme("standard", themes_root),
        serial_writer=DryRunSerialWriter(),
    )

    result = service.handle_status(
        {
            "state": "success",
            "message": "Ready",
            "hook_event_name": "stop",
        }
    )
    assert result["gif"] == "assets/stop.gif"
    service.close()
