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


def test_model_params_surface_effort_and_raw_id():
    status = map_hook_event(
        _event(
            "afterAgentThought",
            duration_ms=500,
            model="claude-opus-4-7-thinking-max",
            model_id="claude-opus-4-7-thinking-max",
            model_params=[
                {"id": "thinking", "value": "true"},
                {"id": "effort", "value": "max"},
                {"id": "context", "value": "1m"},
            ],
        )
    )
    assert status is not None
    assert status.model_id == "claude-opus-4-7-thinking-max"
    assert status.model_label == "claude-opus-4-7-thinking-max"
    assert status.effort == "max"
    assert status.metadata["thinking"] == "true"
    assert status.metadata["context"] == "1m"
    assert "claude-opus-4-7-thinking-max" in status.serial_line()
    assert "max" in status.serial_line()
    assert "·" not in status.serial_line()
    assert status.serial_line().count("|") >= 3


def test_before_submit_prompt_summarizes_attachments():
    status = map_hook_event(
        _event(
            "beforeSubmitPrompt",
            prompt="Fix the flaky test",
            attachments=[
                {"type": "file", "file_path": "a.py"},
                {"type": "file", "file_path": "b.py"},
                {"type": "rule", "file_path": "rule.mdc"},
            ],
        )
    )
    assert status is not None
    assert status.state == AgentState.WAITING
    assert "+2 files" in status.message
    assert "+1 rule" in status.message
    assert status.metadata["attachment_count"] == 3
    assert status.metadata["attachments_summary"] == "+2 files - +1 rule"


def test_shell_exposes_current_tool_and_sandbox():
    status = map_hook_event(
        _event(
            "beforeShellExecution",
            command="npm test",
            sandbox=True,
            model="gpt-5",
        )
    )
    assert status is not None
    assert status.metadata["current_tool"] == "Shell"
    assert status.metadata["sandbox"] is True
    assert status.message == "npm test"
