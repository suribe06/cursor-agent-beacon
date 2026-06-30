"""Direct CLI module tests (coverage)."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

from cursor_agent_beacon import cli


def test_main_run_subcommand():
    with patch.object(sys, "argv", ["cursor-agent-beacon", "run"]), patch.object(
        cli, "run_hook_handler", return_value=0
    ) as handler:
        assert cli.main() == 0
        handler.assert_called_once()


def test_main_install_hooks_subcommand(tmp_path: Path):
    with patch.object(sys, "argv", ["cursor-agent-beacon", "install-hooks"]), patch(
        "cursor_agent_beacon.install.verify_package_installed"
    ), patch(
        "cursor_agent_beacon.install.write_user_hooks",
        return_value=tmp_path / "hooks.json",
    ):
        assert cli.main() == 0
