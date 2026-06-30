"""Tests for packaged asset path resolution."""


from cursor_agent_beacon import paths


def test_default_themes_dir_finds_checkout_themes():
    root = paths.default_themes_dir()
    assert (root / "standard" / "manifest.json").is_file()


def test_package_root_points_at_src_tree():
    root = paths.package_root()
    assert (root / "handler.py").is_file()


def test_beacon_command_returns_argv_list():
    cmd = paths.beacon_command()
    assert cmd[-1] == "run"
    assert len(cmd) >= 2
