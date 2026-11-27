"""Map a Cursor hook to an activity-map station. Pure: no I/O."""

from __future__ import annotations

_FILE_WORDS = frozenset(
    {
        "cat",
        "grep",
        "rg",
        "sed",
        "awk",
        "mv",
        "cp",
        "ls",
        "find",
        "head",
        "tail",
        "wc",
        "mkdir",
        "rm",
        "touch",
        "diff",
        "sort",
        "cut",
    }
)
_NET_WORDS = frozenset({"curl", "wget", "gh", "ssh", "scp", "rsync", "ping"})
_NET_PAIRS = frozenset(
    {
        ("git", "push"),
        ("git", "pull"),
        ("git", "fetch"),
        ("git", "clone"),
        ("npm", "install"),
        ("pnpm", "install"),
        ("yarn", "add"),
        ("pip", "install"),
        ("uv", "pip"),
    }
)
_FILE_TOOLS = frozenset(
    {
        "read",
        "write",
        "edit",
        "delete",
        "glob",
        "grep",
        "strreplace",
        "search_replace",
        "applypatch",
        "readfile",
    }
)


def _tokens(command: str) -> list[str]:
    return command.strip().split()[:2]


def shell_station(command: str) -> str:
    """files, network, or shell. Looks at the first two words only."""
    words = [word.lower() for word in _tokens(command)]
    if len(words) >= 2 and (words[0], words[1]) in _NET_PAIRS:
        return "network"
    if words and words[0] in _NET_WORDS:
        return "network"
    if words and words[0] in _FILE_WORDS:
        return "files"
    return "shell"


def tool_station(tool: str) -> str:
    name = tool.strip()
    if not name:
        return "shell"
    if name.startswith("MCP:") or "mcp" in name.lower():
        return "network"
    if name.lower().replace("-", "").replace("_", "") in _FILE_TOOLS:
        return "files"
    return "shell"


def classify(
    hook: str,
    *,
    command: str = "",
    tool: str = "",
    denied: bool = False,
) -> str:
    if denied and hook == "postToolUseFailure":
        return "hooks"
    if hook in {"sessionStart", "sessionEnd", "beforeSubmitPrompt"}:
        return "you"
    if hook in {"afterAgentThought", "afterAgentResponse", "preCompact", "stop"}:
        return "model"
    if hook in {"beforeReadFile", "afterFileEdit"}:
        return "files"
    if hook in {"subagentStart", "subagentStop"}:
        return "agents"
    if hook in {"beforeMCPExecution", "afterMCPExecution"}:
        return "network"
    if hook in {"beforeShellExecution", "afterShellExecution"}:
        return shell_station(command)
    if hook in {"preToolUse", "postToolUse", "postToolUseFailure"}:
        return tool_station(tool)
    return "shell"


def phase_of(hook: str) -> str:
    if hook in {
        "beforeShellExecution",
        "beforeMCPExecution",
        "beforeReadFile",
        "preToolUse",
        "subagentStart",
        "sessionStart",
        "beforeSubmitPrompt",
    }:
        return "start"
    if hook in {"afterAgentThought", "preCompact"}:
        return "instant"
    return "end"
