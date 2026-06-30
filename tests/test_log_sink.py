"""Tests for log sink."""

from io import StringIO

from cursor_agent_beacon.models import AgentState, AgentStatus
from cursor_agent_beacon.sinks.log import LogStatusSink


def test_log_sink_writes_json_line():
    stream = StringIO()
    sink = LogStatusSink(stream=stream)
    sink.publish(
        AgentStatus(
            state=AgentState.IDLE,
            message="ok",
            hook_event_name="sessionStart",
        )
    )
    line = stream.getvalue().strip()
    assert '"state":"idle"' in line or '"state": "idle"' in line.replace(" ", "")
