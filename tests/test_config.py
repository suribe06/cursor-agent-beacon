"""Tests for environment configuration."""

from cursor_agent_beacon.config import BeaconConfig, redact_enabled


def test_redact_enabled_defaults_false(monkeypatch):
    monkeypatch.delenv("CURSOR_AGENT_BEACON_REDACT_CONTENT", raising=False)
    assert redact_enabled() is False


def test_redact_enabled_from_env(monkeypatch):
    monkeypatch.setenv("CURSOR_AGENT_BEACON_REDACT_CONTENT", "true")
    assert redact_enabled() is True


def test_beacon_config_from_env(monkeypatch, tmp_path):
    monkeypatch.setenv("CURSOR_AGENT_BEACON_LOG", "false")
    monkeypatch.setenv("CURSOR_AGENT_BEACON_FILE", "false")
    monkeypatch.setenv("CURSOR_AGENT_BEACON_REDACT_CONTENT", "1")
    monkeypatch.setenv("CURSOR_AGENT_BEACON_HTTP_URL", "http://127.0.0.1:9999/status")
    monkeypatch.setenv("CURSOR_AGENT_BEACON_STATUS_FILE", str(tmp_path / "status.json"))

    config = BeaconConfig.from_env()
    assert config.enable_log_sink is False
    assert config.enable_file_sink is False
    assert config.redact_content is True
    assert config.http_url == "http://127.0.0.1:9999/status"
