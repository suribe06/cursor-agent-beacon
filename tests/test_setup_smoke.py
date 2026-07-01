"""Smoke test for ./setup.sh end-user install path."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.smoke


def test_setup_sh_installs_hooks_in_isolated_home(tmp_path: Path):
    repo_root = Path(__file__).resolve().parents[1]
    home = tmp_path / "home"
    home.mkdir()
    env = os.environ.copy()
    env["HOME"] = str(home)

    result = subprocess.run(
        [str(repo_root / "setup.sh"), "--hooks-only", "--no-gnome"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout

    hooks_json = home / ".cursor" / "hooks.json"
    wrapper = home / ".cursor" / "hooks" / "cursor-agent-beacon.sh"
    assert hooks_json.is_file()
    assert wrapper.is_file() and os.access(wrapper, os.X_OK)

    payload = json.loads(hooks_json.read_text(encoding="utf-8"))
    assert "sessionStart" in payload.get("hooks", {})

    beacon = repo_root / ".venv" / "bin" / "cursor-agent-beacon"
    assert beacon.is_file()

    doctor = subprocess.run(
        [str(beacon), "doctor", "--probe"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert doctor.returncode == 0, doctor.stderr + doctor.stdout
    assert (home / ".local/share/cursor-agent-beacon/status.json").is_file()
