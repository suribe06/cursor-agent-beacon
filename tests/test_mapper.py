"""Tests for hook event mapping."""

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


def test_before_shell_execution_maps_to_running_shell():
    status = map_hook_event(_event("beforeShellExecution", command="npm test"))
    assert status is not None
    assert status.state == AgentState.RUNNING_SHELL
    assert status.message == "npm test"


def test_after_agent_thought_maps_to_thinking():
    status = map_hook_event(
        _event("afterAgentThought", duration_ms=1200, text="thinking...")
    )
    assert status is not None
    assert status.state == AgentState.THINKING
    assert "1200ms" in status.message


def test_after_shell_execution_detects_failure():
    status = map_hook_event(
        _event(
            "afterShellExecution",
            command="npm test",
            output="Error: command failed with exit code 1",
        )
    )
    assert status is not None
    assert status.state == AgentState.ERROR


def test_after_shell_success_returns_to_thinking():
    status = map_hook_event(
        _event("afterShellExecution", command="echo ok", output="hello\n")
    )
    assert status is not None
    assert status.state == AgentState.THINKING


def test_post_tool_use_returns_to_thinking():
    status = map_hook_event(_event("postToolUse", tool_name="Read"))
    assert status is not None
    assert status.state == AgentState.THINKING


def test_after_agent_response_maps_to_success():
    status = map_hook_event(_event("afterAgentResponse", text="All done."))
    assert status is not None
    assert status.state == AgentState.SUCCESS
    assert status.message == "All done."


def test_stop_completed_maps_to_success():
    status = map_hook_event(_event("stop", status="completed", loop_count=0))
    assert status is not None
    assert status.state == AgentState.SUCCESS
    assert status.message == "Ready"


def test_before_mcp_execution_extracts_tool_name():
    status = map_hook_event(
        _event(
            "beforeMCPExecution",
            tool_name="MCP:github:search_repositories",
            tool_input={"query": "cursor hooks"},
        )
    )
    assert status is not None
    assert status.state == AgentState.RUNNING_MCP
    assert "github:search_repositories" in status.message
