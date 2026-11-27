# Activity Map Plan

Milestone 1 (event log and station classifier) is on `feat/activity-map`. The GNOME popup and the VIEWE status screen both read `events/<id>.summary.json` (seven station dots). The browser map CLI and Hermes are not started.

Proposed feature: a live activity map of what the Cursor agent is doing — tool calls, files, shell, MCP, and subagents — in an on-demand local view.

Inspired by [Lot Map for Claude Code](https://github.com/alexeyw/lot-map) (`alexeyw/lot-map`): a pane beside the chat where each tool call or model step sends a pulse from the centre to a station (You, Model, Memory, Files, Shell, Network, Browser, Agents, Skills, Hooks). Lot Map is a Claude Code plugin. It cannot be installed for Cursor or Hermes Agent. The idea travels; the implementation has to be native to this repo.

Research and metrics in [Alternatives considered](#alternatives-considered) were verified from the GitHub API on **23 Nov 2026**, about 11:20–11:35 a.m. Colombia time (America/Bogota, UTC-5). Star counts are not estimates.

## Alternatives considered

No existing tool is a good drop-in “lot-map for Cursor or Hermes.” Closest matches are Claude-only, Cursor-incomplete, tiny or unproven, or a heavy always-on dashboard. Installing any of the Cursor hook-based tools alongside beacon would compete for the same entries in `~/.cursor/hooks.json`.

| Project | Stars (23 Nov 2026) | Last push (Colombia time) | License | Agents | Why not adopted |
| --- | --- | --- | --- | --- | --- |
| [alexeyw/lot-map](https://github.com/alexeyw/lot-map) | 1,137 | 22 Nov 2026, 4:02 p.m. | MIT | Claude Code only | The UX we want, but it is a Claude Code plugin. No Cursor or Hermes support. |
| [hoangsonww/Claude-Code-Agent-Monitor](https://github.com/hoangsonww/Claude-Code-Agent-Monitor) | 1,205 | 22 Nov 2026, 11:58 p.m. | MIT | Claude Code, Cursor, Codex. Not Hermes | Popular local dashboard (Node/React/SQLite, hooks plus Cursor transcript discovery). It is a full always-on control plane (`ccam`, WebSockets, optional desktop app), not a radial live map, and would overlap beacon’s hooks and status files. Conflicts with “no daemons except Hermes.” |
| [cesarandreslopez/sidekick-agent-hub](https://github.com/cesarandreslopez/sidekick-agent-hub) | 91 | 19 Nov 2026, 7:52 a.m. | MIT | Claude Code, Codex, OpenCode | Closest visual cousin (activity map with stations). Does not support Cursor or Hermes. |
| [mishanefedov/agentwatch](https://github.com/mishanefedov/agentwatch) | 18 | 9 Jul 2026 (stale) | MIT | Hermes is full (polls `~/.hermes/state.db`). Cursor is config-only | Local TUI timeline and cost, not a map. Cursor activity “lives in a SQLite database we haven't parsed yet.” Useful as a reference for a read-only Hermes adapter only. |
| [hassan-kamel/hermes-activity](https://github.com/hassan-kamel/hermes-activity) | 17 | 15 Oct 2026, 3:13 a.m. | MIT | Hermes Desktop | Usage heatmap and token breakdowns from `state.db`. Different job: analytics, not a live tool-call map. |
| [bardia-sneyes/activisual](https://github.com/bardia-sneyes/activisual) | 0 | 12 Oct 2026, 1:50 p.m. | MIT | Codex, Claude Code, Pi, OpenCode, Hermes. Not Cursor | Local timeline and constellation graph. Zero stars and no Cursor support. Do not adopt unless a separate Hermes-only dashboard is wanted later. |
| [Kunal-5402/hooklens](https://github.com/Kunal-5402/hooklens) | 4 | 12 Oct 2026, 4:45 a.m. | Apache-2.0 | Claude Code, Codex, Cursor | Python hook → SQLite → local timeline. Closest Cursor-native stack, but a trace UI rather than a map, and it would compete for the same Cursor hooks. |
| [Romstar/session-trace](https://github.com/Romstar/session-trace) (“Agent Graph”) | 0 | 21 Sep 2026, 3:44 p.m. | MIT | Cursor | VSIX plus an ingest server and a live state graph. Visually close, but unproven; starts a server with the editor; hook conflict with beacon. |
| [SArshiaK/agenttrace](https://github.com/SArshiaK/agenttrace) | 0 | 11 Nov 2026, 5:17 a.m. | MIT | Cursor | Hooks append JSONL and a local timeline is served on loopback. Tiny project; hook conflict; no map, no Hermes. |
| [andreas131989/hivemap](https://github.com/andreas131989/hivemap) | 0 | 27 Sep 2026, 3:20 p.m. | MIT | Claude Code only | Tails `~/.claude` transcripts into a web graph and terminal view. Wrong harness. |
| [matthewholliday/catadio](https://github.com/matthewholliday/catadio) | 2 (archived) | 1 Nov 2026, 11:16 a.m. | MIT | Cursor, Claude Code | Archived metrics dashboard; Linux untested; hook conflict. |
| [buluma/Code-Agent-Monitor](https://github.com/buluma/Code-Agent-Monitor) | 0 (archived) | 2 Nov 2026, 8:40 p.m. | MIT | Claims Claude Code, Cursor, Codex | Archived; same family as Claude-Code-Agent-Monitor. |

**Decision:** implement a lot-map-style view in cursor-agent-beacon. The Cursor hook pipeline is the hard part and already exists here.

## Current architecture and gap

Beacon turns native Cursor hook events into glanceable status — GNOME panel, CLI, optional desk display. Details: [Architecture](architecture.md), [Hooks Reference](hooks.md), [GNOME Status Panel](gnome-panel.md).

Today’s data flow:

```text
Cursor hook (stdin JSON)
        │
        ▼
.cursor/hooks.json → hook-handler.py
        │
        ▼
cursor_agent_beacon.handler
        ├── mapper.py           → AgentStatus (one snapshot)
        ├── session_registry.py → registry.json + sessions/<id>.json
        └── sinks/              → stderr log, status.json, optional HTTP POST
                                      │
                                      ▼
                 GNOME panel polls files; optional bridge → VIEWE
```

Supported hooks already cover the map’s raw material: `sessionStart` / `sessionEnd`, `beforeSubmitPrompt`, `afterAgentThought`, shell and MCP before/after, `afterAgentResponse`, `stop`, `preToolUse` / `postToolUse` / `postToolUseFailure`, `subagentStart` / `subagentStop`, `beforeReadFile`, `afterFileEdit`, and `preCompact`. Context can also be estimated from `~/.cursor/projects/*/agent-transcripts/<id>/<id>.jsonl` (see `context_estimate.py`). Hooks are fail-open and must never block Cursor.

**Gap.** The handler collapses each event into a single latest `AgentStatus`. `SessionRegistry` keeps latest-per-conversation snapshots, not a history. There is no station classification, no event log, and no live map UI. [Roadmap](roadmap.md) has no activity-map item yet. The desk-display simulator in `preview/display-simulator.html` is a useful pattern for an on-demand local HTML UI, not a map.

## Goals and non-goals

### Goals

- Show a live, glanceable map of the **current Cursor session**: which stations are active, which calls are in flight, and a short event list.
- Reuse the existing hook handler, mapper summaries, session registry, and display-pref / redaction patterns.
- Ship an on-demand CLI (`cursor-agent-beacon map`) that serves a local page and exits when the user closes it.
- Keep hooks fail-open. A map fault must never change a Cursor permission decision or block a tool call.
- Bind the UI to **loopback only** (`127.0.0.1`).
- Honour `CURSOR_AGENT_BEACON_REDACT_CONTENT` in the event log and in the UI (labels and names, not full prompts or file bodies).
- Design the event schema so an optional Hermes adapter and a later VIEWE frame can feed or consume the same stations.

### Non-goals

- No always-on map daemon, systemd unit, or process that outlives the CLI / GNOME popup. Hermes itself remains the exception; the optional Hermes adapter must not introduce a new background service.
- Not a Claude Code port, a fork of lot-map, or a hook installer that replaces beacon’s existing `~/.cursor/hooks.json` entries.
- Not a cost/token analytics product (Hermes already has [hermes-activity](https://github.com/hassan-kamel/hermes-activity) for usage heatmaps).
- Not a security or enforcement boundary, and not a transcript scraper as the live path (transcripts stay a fallback for context size, as they are today).
- Not a multi-harness control plane (no Codex / Claude Code / OpenCode coverage in the MVP).
- No cloud telemetry, accounts, or binds on non-loopback interfaces.
- This plan does not schedule implementation. Do not edit README, roadmap, or code until work is explicitly started.

## Design

### Event log sink

Add a new sink beside the existing log / file / HTTP sinks. On every mapped hook that produces an `AgentStatus` (and on paired tool start/end even when the panel state is unchanged), append one JSON line to a per-conversation log.

- Fail-open: I/O errors are logged to stderr and must not raise into the hook handler.
- The snapshot sinks and `SessionRegistry` stay as they are. The GNOME panel keeps polling `status.json` + `registry.json`.
- Redact before write when `CURSOR_AGENT_BEACON_REDACT_CONTENT` is true (same flag the status file already uses). Even when redaction is off, do not persist full file contents, full prompt bodies, or shell stdout — only a short label (command name, tool name, relative path, first line truncated).
- Pair `before*` / `preToolUse` with the matching `after*` / `postToolUse` / `postToolUseFailure` under a `call_id` when Cursor provides one; otherwise synthesise a short-lived id from `conversation_id` + `generation_id` + hook sequence.

### Event schema

One JSON object per line. Draft fields (names can tighten in implementation, but the shape should stay stable):

| Field | Type | Purpose |
| --- | --- | --- |
| `schema` | `1` | Schema version |
| `ts` | string | UTC ISO-8601 timestamp |
| `conversation_id` | string or null | Cursor conversation id (sanitised like `safe_conversation_id`) |
| `generation_id` | string or null | Cursor generation id when present |
| `source` | string | `cursor` (MVP), later `hermes` |
| `hook_event_name` | string | Original Cursor hook name (Hermes events use a stable alias) |
| `station` | string | Classifier output: `you`, `model`, `files`, `shell`, `network`, `agents`, `hooks` |
| `phase` | string | `start`, `end`, `instant` |
| `call_id` | string or null | Pairs start/end of one tool or shell call |
| `state` | string | Beacon `AgentState` value (`thinking`, `running_shell`, …) |
| `label` | string | Short human label already produced by `mapper.py` (truncated) |
| `detail` | object | Small structured extras: tool name, MCP server, relative path, subagent type, exit status, `denied` |
| `model` / `model_id` / `effort` | string or omitted | Sticky, same rules as the session registry |
| `context_usage_percent` | number or omitted | From `preCompact` or transcript estimate |
| `redacted` | boolean | True when content was stripped |

Omit secret-bearing keys. No raw stdin payload dump in the log.

### Station classifier

A small `classify` module (new, beside `mapper.py`) maps each hook — and, for shell/MCP/tool events, the tool or command name — to a station. Default mapping:

| Station | Cursor hooks / signals |
| --- | --- |
| `you` | `sessionStart`, `sessionEnd`, `beforeSubmitPrompt` (and permission-ask prompts when we can see them) |
| `model` | `afterAgentThought`, `afterAgentResponse`, `preCompact`, `stop` |
| `files` | `beforeReadFile`, `afterFileEdit`; shell commands that only read, search, or edit files (`cat`, `grep`, `sed`, `mv`, …) — same idea as lot-map, kept conservative |
| `shell` | `beforeShellExecution` / `afterShellExecution` when the command is not classified as `files` or `network` |
| `network` | `beforeMCPExecution` / `afterMCPExecution`; shell commands known to reach the network (`curl`, `gh`, `ssh`, `git push`, `npm install`, …) |
| `agents` | `subagentStart`, `subagentStop` |
| `hooks` | `postToolUseFailure` when the user or a hook denied the call; otherwise failures stay on the tool’s own station in red |

`preToolUse` / `postToolUse` take the station of the named tool (file tools → `files`, MCP → `network`, otherwise `shell` or `model`). Unknown tools default to `shell` rather than inventing a Skills station in the MVP (Cursor does not expose a skills hook comparable to Claude Code’s).

Classification must be pure and tested: given a hook name + a short command or tool string, the station is deterministic. Do not read command arguments beyond what is needed to decide the station (and redact those arguments before persist).

### Storage and retention

Default root stays `~/.local/share/cursor-agent-beacon/` (already used by the file sink and GNOME panel). New layout:

| Path | Purpose |
| --- | --- |
| `events/<conversation_id>.jsonl` | Append-only event log for one chat |
| `events/` | Directory created on demand |

Reuse `safe_conversation_id` so names stay filesystem-safe and ≤64 characters. If `conversation_id` is missing, write to `events/unknown.jsonl` only as a last resort (and still include `generation_id` in the line).

Retention should follow the session registry’s housekeeping, not grow forever:

- Prune event files for conversations the registry would already prune (inactive sessions; today that is on the order of **7 days**).
- Cap each file (suggested starting point: last **5,000** lines or **2 MB**, whichever first). On overflow, drop the oldest lines or rotate to `events/<id>.jsonl.old` and keep only the newest file in the UI.
- Do not pre-create a SQLite database for the MVP. JSONL keeps the sink dependency-free, matches existing “no required deps” packaging, and is easy to tail.

An environment override is optional later (`CURSOR_AGENT_BEACON_EVENTS_DIR`); the MVP can hard-default next to the status file. Hook latency budget stays in the same range as today (handler timeouts are 5s, 30s on `stop` / `afterAgentResponse`). Appending one short JSON line must stay well under that.

### Map CLI and local UI

New command: `cursor-agent-beacon map`.

```bash
cursor-agent-beacon map                  # focused / most recent active session
cursor-agent-beacon map --id <conversation_id>
```

Behaviour:

- Bind **`127.0.0.1` only**, on an ephemeral or fixed high port (for example `8766`, adjacent to the bridge’s `8765`, or `0` for automatic). Refuse to listen on `0.0.0.0`.
- Serve a single-page UI (static HTML/CSS/JS, in the spirit of `preview/display-simulator.html`) plus a loopback API:
  - `GET /` — map page
  - `GET /api/session` — latest registry snapshot (id, label, model, context)
  - `GET /api/events` — events since a cursor (byte offset or event count)
  - `GET /api/stream` — optional **SSE** of new lines as they are appended
- Open the browser to `http://127.0.0.1:<port>/` when possible; print the URL if not.
- The process is foreground and **exits when the user stops it** (Ctrl+C, or the page sends a close beacon / the last SSE client disconnects after a short grace period). No systemd unit, no leftover server.
- If the event log does not exist yet, show an empty map and wait; hooks will create it on the next agent turn.

UI (MVP):

- Radial board with stations `you`, `model`, `files`, `shell`, `network`, `agents`, and `hooks`.
- A pulse from the centre to the station on `phase=start`, and back on `phase=end`. In-flight calls stay lit; errors and denials render red.
- A short event list under the map (latest labels, no full payloads).
- Context ring around the centre when `context_usage_percent` is known (reuse the panel’s estimate vs `preCompact` distinction; mark estimates with `~` as the GNOME panel does).
- Honour `display.toml` show/hide prefs where they apply (model, context, message). Honour redaction: if `redacted` is true, the list shows the station and a placeholder, not the label text that was stripped.

The map is a **viewer**. It does not install hooks, mutate Cursor settings, or post back into the agent.

### GNOME integration

After the CLI map works, the existing panel (`gnome-extension/`) can grow a light entry point. The panel already polls files; it must not start a background HTTP server of its own.

Suggested steps (milestone 3, not MVP):

- An “Open activity map” action in the popup that runs `cursor-agent-beacon map --id <focused>` (or opens the URL if the user already started the CLI).
- Optionally a compact SVG or CSS sketch of stations in the popup (in-flight dots only), reading the **tail** of `events/<id>.jsonl` or a tiny derived `events/<id>.summary.json` that the sink rewrites on each append. Prefer the summary file if tailing JSONL from GJS is awkward. That summary is a cache, not a second source of truth.
- No new Shell-owned daemon. If the CLI is not running, the compact popup sketch can still render the last N events from disk.

### Optional Hermes adapter

Out of scope for the Cursor MVP. Design constraint for later (milestone 4):

- **Read-only** access to `~/.hermes/state.db` (SQLite), in the same spirit as agentwatch, **only while `cursor-agent-beacon map` is running**.
- No new always-on watcher, no writes to Hermes files, no plugin install required for a first adapter. A later Hermes plugin that POSTs into the same event schema is an alternative, not a requirement.
- Normalise Hermes session / tool-call rows into the same JSONL schema with `source: "hermes"` and a distinct `conversation_id` namespace (for example `hermes:<id>`) so Cursor and Hermes sessions do not collide.
- Do not print or copy secrets, profile `.env` files, or credential stores. If the DB is locked or missing, the UI shows “Hermes unavailable” and keeps serving Cursor events.
- `hermes-activity` remains the usage-analytics tool; this adapter is live activity only.

### Station row on the panel and the desk display

The hook writes `events/<conversation_id>.summary.json` (`flags` is seven characters: you, model, files, shell, network, agents, hooks; `0` idle, `1` hot, `2` error). The GNOME card draws those dots. The bridge sends `MAP|<flags>|<label>` after `STATUS` when the summary changes. Firmware lights the same seven dots on the status screen (`Y M F S N A H`). The browser map CLI is still not built. Hermes is still out.

### Optional VIEWE frame

The compact station row above is on the status screen. A separate map page is not.

## Milestones

Milestone 1 is done on this branch. The station row (popup and desk display) is in. The browser map and Hermes are not started.

### 1. Event log and stations — about 1–2 days

- New classify module + event-log sink, wired from the existing handler without changing hook fail-open behaviour.
- JSONL written under `~/.local/share/cursor-agent-beacon/events/`.
- Redaction honouring `CURSOR_AGENT_BEACON_REDACT_CONTENT`.
- Retention hooks plugged into session housekeeping (or an equivalent prune in the sink).

**Acceptance**

- A simulated hook sequence (`scripts/simulate_hook.py` / existing mapper tests) produces a JSONL file with the expected stations and paired `call_id`s.
- Handler still returns `{"continue": true}` (or the current fail-open response) when the events directory is read-only or the disk is full.
- `status.json` / registry behaviour is unchanged; existing panel tests still pass.
- Redaction tests: with the env flag on, labels do not contain the raw prompt or file body from the fixture.

### 2. On-demand map CLI — about 3–5 days (Cursor MVP)

- `cursor-agent-beacon map` serves the loopback HTML UI and SSE/poll API.
- Radial stations, pulses, event list, context ring for one Cursor conversation.
- Process exits on Ctrl+C / last-client disconnect; bind address is `127.0.0.1`.

**Acceptance**

- `cursor-agent-beacon map --help` is documented in the command itself.
- A doctor or smoke check proves the server refuses a non-loopback bind if one is requested.
- Running the CLI, then replaying hooks, updates the page without a reload (SSE or a documented short poll interval).
- No systemd unit, no new package extra required for the MVP (stdlib HTTP is enough).
- `doctor` remains green and does not require the map server to be running.

### 3. GNOME entry point — about 2–3 days

- Popup action to open the map for the focused session.
- Optional compact in-popup sketch or summary dots.

**Acceptance**

- The station dots read the summary file. They stay idle when that file is missing, and they do not need the map CLI.
- Opening the action launches the CLI or the local URL for the focused `conversation_id`.
- No new background GNOME process after the popup is closed (aside from the existing file polling).

### 4. Optional Hermes adapter — about 2–4 days

- Read-only `~/.hermes/state.db` polling **while the map CLI is open**.
- Hermes sessions appear in the same UI with `source: "hermes"`.

**Acceptance**

- Missing or locked DB does not crash the CLI or break Cursor playback.
- No writes under `~/.hermes/`.
- No Hermes process is started. Stopping the map CLI stops all polling.

**Rough total:** Cursor MVP (milestones 1–2) about **1.5–2 weeks**. With GNOME and Hermes, about **3 weeks**.

When implementation starts, add a short link from [Roadmap](roadmap.md) and the README documentation list — not before.

## Testing

Reuse the current toolchain: `pytest -m "not smoke"`, `ruff`, `pyright` (see the README development section).

| Layer | What to cover |
| --- | --- |
| Classifier | Table-driven tests: hook name + command/tool → station. Include file-like vs network-like shell commands, MCP names, subagents, denials. |
| Sink | Temp directory fixtures: append, pairing, rotation/cap, prune of stale conversation files, permission errors fail open. |
| Redaction | Same fixture with `CURSOR_AGENT_BEACON_REDACT_CONTENT` on and off. |
| Handler integration | Existing hook/mapper/integration tests still pass; one new test that a full hook sequence writes JSONL and a status snapshot. |
| CLI / HTTP | Bind 127.0.0.1; reject `0.0.0.0` if a bind option exists; `/api/events` resumes from an offset; SSE or poll delivers a newly appended line. |
| GNOME (later) | Manual check on Ubuntu / GNOME Shell 46–50; do not require the map server for the status card. Preview HTML can cover the compact sketch if one is added. |
| Hermes (later) | Tests against a **fixture** SQLite file, never a live profile DB in CI. |

Do not add end-to-end tests that call a real Cursor or Hermes instance in CI. `scripts/simulate_hook.py` remains the local probe.

## Risks and open questions

- **Hook payload shape.** Cursor may omit a stable `call_id`. Pairing start/end could be imperfect when several shells run at once. The classifier and UI should tolerate unmatched `start` events (leave the station lit until `stop` / `afterAgentResponse`, then clear).
- **Hook coverage vs lot-map.** Beacon will not see every Claude Code concept (skills catalogue, memory folder, browser tools) unless Cursor emits a hook for them. Do not fake stations with no data.
- **Latency.** The hook handler must stay fail-open and fast. If JSONL rotation ever becomes expensive, do it outside the hook path (for example on map CLI start, or when the registry prunes).
- **GNOME vs CLI.** Reading a growing JSONL from GJS may be awkward; a sink-written summary file may be the safer popup path.
- **Hermes schema drift.** `state.db` is not a public, versioned API. The adapter should isolate SQL behind a small module and treat unknown tables as “unavailable.”
- **Port clashes.** Default map port vs the bridge (`8765`) and vs other local tools. Prefer an automatic free loopback port and print it.
- **Retention vs replay.** Aggressive prune is right for privacy; users who want a long replay may want a knob later. Not in the MVP.
- **Redaction vs usefulness.** Over-redaction makes the map a set of anonymous pulses. Default should match today’s status-file behaviour (flag off unless the user sets it), while still omitting full bodies even when the flag is off.
- **Unreleased vault work.** `feat/obsidian-vault-page` has VIEWE `GRAPH|` work that is not on `main`. A later VIEWE map frame should be designed against whatever protocol is already merged, not against that branch.

## Implementation note

**Do not start this work on `feat/obsidian-vault-page`.** That branch is ahead of `origin/main` with unreleased VIEWE vault-graph and related changes. When implementation is approved, branch from **`main`** (for example `feat/activity-map`) and keep this plan’s scope off the vault-page work.

This file is the plan. No code, hook, or packaging changes belong in the same change as adding the document.
