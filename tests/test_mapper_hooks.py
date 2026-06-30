"""Parametrized mapper coverage."""

import pytest

from cursor_agent_beacon.hooks import SUPPORTED_HOOKS, is_supported_hook
from cursor_agent_beacon.mapper import map_hook_event
from cursor_agent_beacon.models import AgentState, HookEvent


def _event(name: str, **fields):
    payload = {
        "hook_event_name": name,
        "conversation_id": "conv-1",
        "generation_id": "gen-1",
        **fields,
    }
    return HookEvent.from_dict(payload)


@pytest.mark.parametrize("hook_name", SUPPORTED_HOOKS)
def test_supported_hooks_map_to_status(hook_name: str):
    assert is_supported_hook(hook_name)
    extras = {
        "beforeSubmitPrompt": {"prompt": "hello"},
        "afterAgentThought": {"duration_ms": 10},
        "beforeShellExecution": {"command": "ls"},
        "afterShellExecution": {"command": "ls", "output": "ok", "exit_code": 0},
        "beforeMCPExecution": {"tool_name": "MCP:foo:bar"},
        "afterMCPExecution": {"tool_name": "MCP:foo:bar"},
        "afterAgentResponse": {"text": "done"},
        "stop": {"status": "completed"},
        "preToolUse": {"tool_name": "Read"},
        "postToolUse": {"tool_name": "Read"},
        "postToolUseFailure": {"tool_name": "Read"},
        "subagentStart": {"subagent_type": "explore"},
        "subagentStop": {"status": "completed"},
        "beforeReadFile": {"path": "/tmp/example.txt"},
        "afterFileEdit": {
            "file_path": "src/foo.py",
            "edits": [{"old_string": "a", "new_string": "b"}],
        },
        "preCompact": {"trigger": "auto"},
        "sessionEnd": {"reason": "logout"},
    }
    status = map_hook_event(_event(hook_name, **extras.get(hook_name, {})))
    assert status is not None
    assert status.state in AgentState


def test_shell_failure_uses_exit_code():
    status = map_hook_event(
        _event("afterShellExecution", command="false", output="", exit_code=1)
    )
    assert status is not None
    assert status.state == AgentState.ERROR


def test_redact_prompt(monkeypatch):
    monkeypatch.setenv("CURSOR_AGENT_BEACON_REDACT_CONTENT", "true")
    status = map_hook_event(_event("beforeSubmitPrompt", prompt="secret prompt"))
    assert status is not None
    assert "secret" not in status.message


def test_before_read_file_maps_to_thinking():
    status = map_hook_event(_event("beforeReadFile", path="/tmp/foo.py"))
    assert status is not None
    assert status.state == AgentState.THINKING
    assert "foo.py" in status.message


def test_after_file_edit_maps_to_editing():
    status = map_hook_event(
        _event(
            "afterFileEdit",
            file_path="src/cursor_agent_beacon/mapper.py",
            edits=[{"old_string": "x", "new_string": "y"}],
        )
    )
    assert status is not None
    assert status.state == AgentState.THINKING
    assert "mapper.py" in status.message
    assert status.metadata["edit_count"] == 1


def test_pre_compact_maps_to_compacting():
    status = map_hook_event(_event("preCompact", trigger="manual"))
    assert status is not None
    assert status.state == AgentState.THINKING
    assert status.message == "Compacting context..."
    assert status.metadata["trigger"] == "manual"


def test_redact_file_edit(monkeypatch):
    monkeypatch.setenv("CURSOR_AGENT_BEACON_REDACT_CONTENT", "true")
    status = map_hook_event(
        _event("afterFileEdit", file_path="/secret/path.txt", edits=[])
    )
    assert status is not None
    assert "secret" not in status.message
    assert status.message == "Editing file..."
