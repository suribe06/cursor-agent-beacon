"""Direct CLI module tests (coverage)."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

from cursor_agent_beacon import cli


def test_main_run_subcommand():
    with (
        patch.object(sys, "argv", ["cursor-agent-beacon", "run"]),
        patch.object(cli, "run_hook_handler", return_value=0) as handler,
    ):
        assert cli.main() == 0
        handler.assert_called_once()


def test_main_install_hooks_subcommand(tmp_path: Path):
    with (
        patch.object(sys, "argv", ["cursor-agent-beacon", "install-hooks"]),
        patch("cursor_agent_beacon.install.verify_package_installed"),
        patch(
            "cursor_agent_beacon.install.write_user_hooks",
            return_value=tmp_path / "hooks.json",
        ),
    ):
        assert cli.main() == 0


def test_main_setup_subcommand(tmp_path: Path):
    from cursor_agent_beacon.setup import SetupResult

    fake = SetupResult(
        hooks_path=tmp_path / "hooks.json",
        status_file=tmp_path / "status.json",
        beacon_bin=tmp_path / "beacon",
    )
    with (
        patch.object(sys, "argv", ["cursor-agent-beacon", "setup"]),
        patch("cursor_agent_beacon.setup.run_setup", return_value=fake),
    ):
        assert cli.main() == 0


def test_main_doctor_subcommand():
    from cursor_agent_beacon.doctor import CheckResult

    with (
        patch.object(sys, "argv", ["cursor-agent-beacon", "doctor"]),
        patch(
            "cursor_agent_beacon.doctor.run_doctor",
            return_value=[CheckResult("package", True, "ok")],
        ),
    ):
        assert cli.main() == 0


def test_main_status_subcommand(tmp_path: Path):
    status_file = tmp_path / "status.json"
    status_file.write_text(
        '{"state":"idle","message":"Ready","hook_event_name":"stop"}',
        encoding="utf-8",
    )
    with patch.object(
        sys,
        "argv",
        ["cursor-agent-beacon", "status", "--file", str(status_file)],
    ):
        assert cli.main() == 0


def test_main_uninstall_subcommand():
    with (
        patch.object(sys, "argv", ["cursor-agent-beacon", "uninstall", "--hooks-only"]),
        patch(
            "cursor_agent_beacon.install.uninstall_desktop",
            return_value={
                "hooks_path": Path("/tmp/hooks.json"),
                "gnome_path": None,
                "status_dir": None,
            },
        ),
    ):
        assert cli.main() == 0
