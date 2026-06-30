"""Tests for supported hook registry."""

from cursor_agent_beacon.hooks import SUPPORTED_HOOKS, is_supported_hook


def test_all_supported_hooks_are_recognized():
    for hook in SUPPORTED_HOOKS:
        assert is_supported_hook(hook)


def test_unknown_hook_is_not_supported():
    assert not is_supported_hook("notARealHook")


def test_before_read_file_is_supported():
    assert is_supported_hook("beforeReadFile")
