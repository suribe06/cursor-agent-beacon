"""Tests for transcript-based context estimation."""

from __future__ import annotations

from pathlib import Path

from cursor_agent_beacon.context_estimate import (
    enrich_status_context,
    estimate_context,
    find_transcript,
    learn_bytes_per_token,
    parse_context_window,
)
from cursor_agent_beacon.models import AgentState, AgentStatus


def test_parse_context_window():
    assert parse_context_window("256k") == 256_000
    assert parse_context_window("1m") == 1_000_000
    assert parse_context_window(128000) == 128_000
    assert parse_context_window("nope") is None


def test_learn_bytes_per_token_rejects_outliers():
    assert learn_bytes_per_token(2500, 1000) == 2.5
    assert learn_bytes_per_token(10, 1000) is None
    assert learn_bytes_per_token(50_000, 1000) is None


def test_estimate_from_transcript(tmp_path: Path, monkeypatch):
    cid = "conv-estimate-1"
    project = tmp_path / "proj"
    transcript = project / "agent-transcripts" / cid / f"{cid}.jsonl"
    transcript.parent.mkdir(parents=True)
    # 2500 bytes → 1000 tokens at 2.5 bytes/token → 1000/256000 ≈ 0.39%
    transcript.write_bytes(b"x" * 2500)
    monkeypatch.setenv("CURSOR_AGENT_BEACON_CURSOR_PROJECTS", str(tmp_path))

    assert find_transcript(cid) == transcript
    est = estimate_context(cid, window_size=256_000, bytes_per_token=2.5)
    assert est is not None
    assert est.tokens == 1000
    assert est.window == 256_000
    assert round(est.percent, 2) == 0.39


def test_enrich_estimates_when_missing(tmp_path: Path, monkeypatch):
    cid = "conv-enrich-1"
    project = tmp_path / "proj"
    transcript = project / "agent-transcripts" / cid / f"{cid}.jsonl"
    transcript.parent.mkdir(parents=True)
    transcript.write_bytes(b"y" * 12_800)  # 5120 tokens @ 2.5 → 2% of 256k
    monkeypatch.setenv("CURSOR_AGENT_BEACON_CURSOR_PROJECTS", str(tmp_path))

    status = AgentStatus(
        state=AgentState.THINKING,
        message="Thinking...",
        hook_event_name="afterAgentThought",
        conversation_id=cid,
    )
    enriched = enrich_status_context(status)
    assert enriched.context_tokens == 5120
    assert enriched.context_window_size == 256_000
    assert enriched.metadata["context_source"] == "estimated"
    assert round(enriched.context_usage_percent or 0, 1) == 2.0


def test_enrich_keeps_measured_precompact(tmp_path: Path, monkeypatch):
    cid = "conv-measured-1"
    project = tmp_path / "proj"
    transcript = project / "agent-transcripts" / cid / f"{cid}.jsonl"
    transcript.parent.mkdir(parents=True)
    transcript.write_bytes(b"z" * 10_000)
    monkeypatch.setenv("CURSOR_AGENT_BEACON_CURSOR_PROJECTS", str(tmp_path))

    status = AgentStatus(
        state=AgentState.THINKING,
        message="Compacting context...",
        hook_event_name="preCompact",
        conversation_id=cid,
        context_usage_percent=85.0,
        context_tokens=4000,
        context_window_size=128_000,
        metadata={"context_source": "measured"},
    )
    enriched = enrich_status_context(status)
    assert enriched.context_usage_percent == 85.0
    assert enriched.context_tokens == 4000
    assert enriched.metadata["context_source"] == "measured"
    # 10000 / 4000 = 2.5
    assert enriched.metadata["context_bytes_per_token"] == 2.5
