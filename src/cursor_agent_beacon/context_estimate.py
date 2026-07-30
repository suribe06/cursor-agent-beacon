"""Estimate conversation context usage from Cursor agent transcripts.

Cursor only sends exact context stats on ``preCompact``. Between those
events we approximate from the on-disk transcript so the panel/display
stay roughly in sync with Cursor's Context Usage UI.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# ponytail: Cursor's reported tokens ÷ transcript bytes ≈ 2.5 on agent
# chats (JSON wrapper + omitted system/tools partially cancel). Learn a
# better ratio from the next preCompact when available.
_DEFAULT_BYTES_PER_TOKEN = 2.5
_DEFAULT_WINDOW = 256_000
_SAFE_ID = re.compile(r"[^A-Za-z0-9_.-]+")


@dataclass(frozen=True, slots=True)
class ContextEstimate:
    tokens: int
    window: int
    percent: float
    transcript_bytes: int
    bytes_per_token: float


def safe_conversation_id(conversation_id: str | None) -> str | None:
    if not conversation_id:
        return None
    cleaned = _SAFE_ID.sub("", conversation_id.strip())[:64]
    return cleaned or None


def parse_context_window(value: Any) -> int | None:
    """Parse model_params context like ``256k``, ``1m``, or a raw int."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        n = int(value)
        return n if n > 0 else None
    text = str(value).strip().lower().replace(",", "").replace("_", "")
    if not text:
        return None
    match = re.fullmatch(r"(\d+(?:\.\d+)?)([kmb])?", text)
    if not match:
        try:
            n = int(float(text))
            return n if n > 0 else None
        except ValueError:
            return None
    amount = float(match.group(1))
    suffix = match.group(2)
    mult = {None: 1, "k": 1_000, "m": 1_000_000, "b": 1_000_000_000}[suffix]
    n = int(amount * mult)
    return n if n > 0 else None


def cursor_projects_root() -> Path:
    override = os.environ.get("CURSOR_AGENT_BEACON_CURSOR_PROJECTS")
    if override:
        return Path(override)
    return Path.home() / ".cursor" / "projects"


def find_transcript(conversation_id: str | None) -> Path | None:
    """Locate ``…/agent-transcripts/<id>/<id>.jsonl`` under Cursor projects."""
    cid = safe_conversation_id(conversation_id)
    if not cid:
        return None
    root = cursor_projects_root()
    if not root.is_dir():
        return None
    matches = list(root.glob(f"*/agent-transcripts/{cid}/{cid}.jsonl"))
    if not matches:
        # Older / alternate layout: flat file under agent-transcripts/
        matches = list(root.glob(f"*/agent-transcripts/{cid}.jsonl"))
    if not matches:
        return None
    return max(matches, key=lambda path: path.stat().st_mtime)


def estimate_context(
    conversation_id: str | None,
    *,
    window_size: int | None = None,
    bytes_per_token: float | None = None,
) -> ContextEstimate | None:
    """Return a rough context estimate from the transcript file size."""
    path = find_transcript(conversation_id)
    if path is None:
        return None
    try:
        size = path.stat().st_size
    except OSError:
        return None
    if size <= 0:
        return None

    bpt = float(bytes_per_token or _DEFAULT_BYTES_PER_TOKEN)
    if bpt <= 0:
        bpt = _DEFAULT_BYTES_PER_TOKEN
    window = int(window_size or _DEFAULT_WINDOW)
    if window <= 0:
        window = _DEFAULT_WINDOW

    tokens = max(1, int(round(size / bpt)))
    percent = min(100.0, max(0.0, (tokens / window) * 100.0))
    return ContextEstimate(
        tokens=tokens,
        window=window,
        percent=percent,
        transcript_bytes=size,
        bytes_per_token=bpt,
    )


def learn_bytes_per_token(transcript_bytes: int, measured_tokens: int) -> float | None:
    """Derive a session ratio from a measured preCompact reading."""
    if transcript_bytes <= 0 or measured_tokens <= 0:
        return None
    ratio = transcript_bytes / float(measured_tokens)
    # Keep a sane band so one bad reading cannot explode future estimates.
    if ratio < 0.5 or ratio > 20.0:
        return None
    return ratio


def enrich_status_context(
    status: Any,
    *,
    prior: dict[str, Any] | None = None,
) -> Any:
    """Fill context fields from transcript when Cursor did not send them.

    ``prior`` is the existing session registry entry (sticky window / ratio).
    Measured ``preCompact`` values win for that event and train the ratio.
    """
    from dataclasses import replace

    from cursor_agent_beacon.models import AgentStatus

    if not isinstance(status, AgentStatus):
        return status

    prior = prior or {}
    meta = dict(status.metadata or {})
    measured = (
        status.hook_event_name == "preCompact"
        and status.context_usage_percent is not None
    )

    if measured:
        meta["context_source"] = "measured"
        path = find_transcript(status.conversation_id)
        if path is not None and status.context_tokens:
            try:
                size = path.stat().st_size
            except OSError:
                size = 0
            learned = learn_bytes_per_token(size, status.context_tokens)
            if learned is not None:
                meta["context_bytes_per_token"] = learned
                meta["context_transcript_bytes"] = size
        return replace(status, metadata=meta)

    # Prefer sticky window, then model_params context, then estimate default.
    window = status.context_window_size or _coerce_prior_int(
        prior.get("context_window_size")
    )
    if window is None:
        window = parse_context_window(meta.get("context"))
    if window is None:
        window = parse_context_window(prior.get("metadata", {}).get("context"))

    bpt = meta.get("context_bytes_per_token")
    if bpt is None:
        bpt = prior.get("context_bytes_per_token")
    if bpt is None:
        bpt = (prior.get("metadata") or {}).get("context_bytes_per_token")

    estimate = estimate_context(
        status.conversation_id,
        window_size=window,
        bytes_per_token=float(bpt) if bpt is not None else None,
    )
    if estimate is None:
        return status

    meta["context_source"] = "estimated"
    meta["context_transcript_bytes"] = estimate.transcript_bytes
    meta["context_bytes_per_token"] = estimate.bytes_per_token
    return replace(
        status,
        context_usage_percent=estimate.percent,
        context_tokens=estimate.tokens,
        context_window_size=estimate.window,
        metadata=meta,
    )


def _coerce_prior_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        n = int(value)
    except (TypeError, ValueError):
        return None
    return n if n > 0 else None
