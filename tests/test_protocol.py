"""Tests for the serial line protocol."""

from cursor_agent_beacon.protocol import (
    EventLine,
    StatusCommand,
    ThemeCommand,
    parse_line,
)


def test_parse_status_line():
    parsed = parse_line("STATUS|thinking|Planning next step")
    assert isinstance(parsed, StatusCommand)
    assert parsed.state == "thinking"
    assert parsed.message == "Planning next step"


def test_parse_theme_line():
    parsed = parse_line("THEME|standard")
    assert isinstance(parsed, ThemeCommand)
    assert parsed.theme_id == "standard"


def test_parse_event_line():
    parsed = parse_line("EVENT|button_pressed")
    assert isinstance(parsed, EventLine)
    assert parsed.event_type == "button_pressed"


def test_status_round_trip():
    cmd = StatusCommand(state="success", message="All done")
    assert parse_line(cmd.serial_line()) == cmd


def test_ignores_blank_and_comments():
    assert parse_line("") is None
    assert parse_line("   ") is None
    assert parse_line("# debug") is None
