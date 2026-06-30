"""Tests for install helpers."""

from __future__ import annotations

import json
from pathlib import Path

from cursor_agent_beacon.hooks import SUPPORTED_HOOKS
from cursor_agent_beacon.install import merge_hooks_config, write_user_hooks


def test_merge_hooks_preserves_other_commands(tmp_path: Path):
    existing = {
        "version": 1,
        "hooks": {
            "stop": [
                {"command": "./hooks/other.sh", "timeout": 2},
                {"command": "./hooks/cursor-agent-beacon.sh", "timeout": 5},
            ],
            "customHook": [{"command": "./hooks/custom.sh", "timeout": 1}],
        },
    }
    merged = merge_hooks_config(existing, "./hooks/cursor-agent-beacon.sh")

    assert merged["hooks"]["customHook"] == existing["hooks"]["customHook"]
    stop_cmds = merged["hooks"]["stop"]
    assert stop_cmds[0]["command"] == "./hooks/cursor-agent-beacon.sh"
    assert any(cmd["command"] == "./hooks/other.sh" for cmd in stop_cmds)
    assert len(merged["hooks"]) == len(SUPPORTED_HOOKS) + 1


def test_write_user_hooks_creates_wrapper(tmp_path: Path, monkeypatch):
    cursor_dir = tmp_path / ".cursor"
    status_file = tmp_path / "share/status.json"
    monkeypatch.setattr(
        "cursor_agent_beacon.install.DEFAULT_STATUS_DIR",
        status_file.parent,
    )
    monkeypatch.setattr(
        "cursor_agent_beacon.install.DEFAULT_STATUS_FILE",
        status_file,
    )

    hooks_path = write_user_hooks(cursor_dir=cursor_dir, status_file=status_file)

    wrapper = cursor_dir / "hooks" / "cursor-agent-beacon.sh"
    assert wrapper.is_file()
    assert "cursor-agent-beacon run" in wrapper.read_text(encoding="utf-8")

    payload = json.loads(hooks_path.read_text(encoding="utf-8"))
    hook_cmd = payload["hooks"]["beforeReadFile"][0]["command"]
    assert hook_cmd == "./hooks/cursor-agent-beacon.sh"
