"""Station classifier is pure and deterministic."""

import pytest

from cursor_agent_beacon.stations import classify

CASES = [
    ("sessionStart", "", "", False, "you"),
    ("beforeSubmitPrompt", "", "", False, "you"),
    ("afterAgentThought", "", "", False, "model"),
    ("stop", "", "", False, "model"),
    ("beforeReadFile", "", "", False, "files"),
    ("afterFileEdit", "", "", False, "files"),
    ("beforeShellExecution", "grep -n foo src", "", False, "files"),
    ("beforeShellExecution", "git push origin main", "", False, "network"),
    ("beforeShellExecution", "curl https://example.com", "", False, "network"),
    ("beforeShellExecution", "npm test", "", False, "shell"),
    ("beforeMCPExecution", "", "MCP:github:list", False, "network"),
    ("preToolUse", "", "Read", False, "files"),
    ("preToolUse", "", "MCP:server:tool", False, "network"),
    ("preToolUse", "", "UnknownWidget", False, "shell"),
    ("subagentStart", "", "", False, "agents"),
    ("postToolUseFailure", "", "Read", True, "hooks"),
    ("postToolUseFailure", "", "Read", False, "files"),
]


@pytest.mark.parametrize(("hook", "command", "tool", "denied", "station"), CASES)
def test_classify(hook, command, tool, denied, station):
    assert classify(hook, command=command, tool=tool, denied=denied) == station
