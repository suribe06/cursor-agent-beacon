"""Tests for multi-session registry."""

from pathlib import Path

from cursor_agent_beacon.models import AgentState, AgentStatus
from cursor_agent_beacon.session_registry import (
    SessionRegistry,
    is_busy_state,
    pick_auto_focus,
    safe_conversation_id,
)


def _status(
    *,
    conversation_id: str = "conv-1",
    state: AgentState = AgentState.THINKING,
    hook: str = "afterAgentThought",
    message: str = "Thinking...",
    project: str = "beacon",
    label: str = "Fix hooks",
) -> AgentStatus:
    return AgentStatus(
        state=state,
        message=message,
        hook_event_name=hook,
        conversation_id=conversation_id,
        project=project,
        label=label,
        timestamp="2026-06-26T18:00:00+00:00",
    )


def test_safe_conversation_id_strips_unsafe_chars():
    assert safe_conversation_id("abc/123?x") == "abc123x"


def test_pick_auto_focus_prefers_busy_session():
    sessions = [
        {
            "id": "a",
            "state": "success",
            "updated_at": "2026-06-26T18:00:02+00:00",
            "active": True,
        },
        {
            "id": "b",
            "state": "running_shell",
            "updated_at": "2026-06-26T18:00:01+00:00",
            "active": True,
        },
    ]
    focused = pick_auto_focus(sessions)
    assert focused is not None
    assert focused["id"] == "b"


def test_registry_writes_session_files_and_index(tmp_path: Path):
    registry = SessionRegistry(tmp_path)
    registry.publish(_status(conversation_id="conv-a"))
    registry.publish(
        _status(
            conversation_id="conv-b",
            state=AgentState.RUNNING_SHELL,
            hook="beforeShellExecution",
            message="npm test",
            project="mafpin",
            label="Run tests",
        )
    )

    index = (tmp_path / "registry.json").read_text(encoding="utf-8")
    assert "conv-a" in index
    assert "conv-b" in index
    assert (tmp_path / "sessions" / "conv-a.json").exists()
    assert (tmp_path / "sessions" / "conv-b.json").exists()

    status = (tmp_path / "status.json").read_text(encoding="utf-8")
    assert "active_count" in status
    assert "focused_conversation_id" in status


def test_session_end_marks_inactive(tmp_path: Path):
    registry = SessionRegistry(tmp_path)
    registry.publish(_status(conversation_id="conv-a"))
    registry.publish(
        _status(
            conversation_id="conv-a",
            state=AgentState.IDLE,
            hook="sessionEnd",
            message="Session ended",
        )
    )

    payload = (tmp_path / "sessions" / "conv-a.json").read_text(encoding="utf-8")
    assert '"active": false' in payload


def test_is_busy_state():
    assert is_busy_state("thinking")
    assert not is_busy_state("success")
