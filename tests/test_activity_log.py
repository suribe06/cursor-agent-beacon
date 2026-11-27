"""Activity JSONL: stations, pairing, cap, prune, fail-open, redaction."""

import json
import os
from io import StringIO
from pathlib import Path

from cursor_agent_beacon.activity import append_activity
from cursor_agent_beacon.config import BeaconConfig
from cursor_agent_beacon.handler import run_hook_handler
from cursor_agent_beacon.models import HookEvent
from cursor_agent_beacon.sinks.file import FileStatusSink


def _event(payload: dict) -> HookEvent:
    return HookEvent.from_dict(payload)


def _lines(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


def test_hook_sequence_pairs_shell_calls(tmp_path: Path):
    root = tmp_path / "data"
    shared = {
        "conversation_id": "conv/1",
        "generation_id": "gen-9",
        "command": "grep secret src",
    }
    sink = FileStatusSink(root / "status.json")
    config = BeaconConfig(status_file=root / "status.json", enable_log_sink=False)
    for name in ("beforeShellExecution", "afterShellExecution"):
        code = run_hook_handler(
            stdin=StringIO(json.dumps({"hook_event_name": name, **shared})),
            stdout=StringIO(),
            stderr=StringIO(),
            sink=sink,
            config=config,
        )
        assert code == 0

    events = _lines(root / "events" / "conv1.jsonl")
    assert [item["station"] for item in events] == ["files", "files"]
    assert events[0]["phase"] == "start"
    assert events[1]["phase"] == "end"
    assert events[0]["call_id"] == events[1]["call_id"]
    assert events[0]["call_id"]
    status = json.loads((root / "status.json").read_text(encoding="utf-8"))
    assert status["state"] == "thinking"


def test_redaction_strips_prompt(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("CURSOR_AGENT_BEACON_REDACT_CONTENT", "1")
    root = tmp_path / "data"
    secret = "SUPER_SECRET_PROMPT_BODY"
    code = run_hook_handler(
        stdin=StringIO(
            json.dumps(
                {
                    "hook_event_name": "beforeSubmitPrompt",
                    "conversation_id": "c1",
                    "prompt": secret,
                }
            )
        ),
        stdout=StringIO(),
        stderr=StringIO(),
        sink=FileStatusSink(root / "status.json"),
        config=BeaconConfig(
            status_file=root / "status.json",
            redact_content=True,
            enable_log_sink=False,
        ),
    )
    assert code == 0
    text = (root / "events" / "c1.jsonl").read_text(encoding="utf-8")
    assert secret not in text
    assert json.loads(text)["redacted"] is True
    assert json.loads(text)["label"] == "you"


def test_readonly_events_dir_fails_open(tmp_path: Path, capsys):
    blocker = tmp_path / "not-a-directory"
    blocker.write_text("x", encoding="utf-8")
    stdout = StringIO()
    code = run_hook_handler(
        stdin=StringIO(
            json.dumps(
                {
                    "hook_event_name": "beforeSubmitPrompt",
                    "conversation_id": "c1",
                    "prompt": "hi",
                }
            )
        ),
        stdout=stdout,
        stderr=StringIO(),
        sink=FileStatusSink(tmp_path / "status.json"),
        config=BeaconConfig(
            status_file=blocker / "status.json",
            enable_log_sink=False,
        ),
    )
    assert code == 0
    assert json.loads(stdout.getvalue())["continue"] is True
    assert "activity log failed" in capsys.readouterr().err


def test_cap_drops_oldest_lines(tmp_path: Path):
    root = tmp_path
    event = _event(
        {
            "hook_event_name": "afterAgentThought",
            "conversation_id": "c1",
        }
    )
    from cursor_agent_beacon.mapper import map_hook_event

    status = map_hook_event(event)
    for _ in range(6):
        append_activity(event, status, root=root, max_lines=3, max_bytes=10_000)
    lines = _lines(root / "events" / "c1.jsonl")
    assert len(lines) == 3


def test_prune_drops_stale_conversation_files(tmp_path: Path):
    events = tmp_path / "events"
    events.mkdir()
    old = events / "gone.jsonl"
    old.write_text("{}\n", encoding="utf-8")
    os.utime(old, (1, 1))
    fresh = events / "keep.jsonl"
    fresh.write_text("{}\n", encoding="utf-8")
    (tmp_path / "registry.json").write_text(
        json.dumps({"sessions": [{"id": "keep"}]}),
        encoding="utf-8",
    )
    event = _event({"hook_event_name": "stop", "conversation_id": "keep"})
    from cursor_agent_beacon.mapper import map_hook_event

    append_activity(event, map_hook_event(event), root=tmp_path)
    assert not old.exists()
    assert fresh.exists()
