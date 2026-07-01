# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.1] - 2026-06-30

### Fixed

- PyPI publish: drop SPDX `license` field (Metadata 2.4) and use official `pypa/gh-action-pypi-publish`

## [0.3.0] - 2026-06-30

### Added

- **`./setup.sh`**: one-shot install (venv → pip → hooks + GNOME panel)
- **`cursor-agent-beacon setup`**: same flow after `pip install`
- **`cursor-agent-beacon doctor`**: verify hooks, wrapper, status dir; `--probe` for end-to-end test
- **`cursor-agent-beacon status`**: human-readable status snapshot
- **`cursor-agent-beacon uninstall`**: remove hooks, GNOME panel; `--purge-status` to delete status data
- **PyPI install path**: `pip install "cursor-agent-beacon[bridge]"` then `cursor-agent-beacon setup`
- **GNOME status panel** (v0.10 pre-release): `gnome-extension/` + install scripts
- **Multi-session file sink**: `registry.json`, `sessions/<id>.json`, auto-focused `status.json`
- `scripts/install-desktop.sh`, `install-user-hooks.sh`, `install-gnome-panel.sh` (wrappers around `setup.sh`)
- `docs/gnome-panel.md`
- Session registry (`session_registry.py`) with per-conversation status and busy-session focus
- Hooks: `beforeReadFile`, `afterFileEdit`, `preCompact` mapped
- Example event: `post_tool_use_permission_denied.json`
- Release workflow on version tags; PyPI publish on tag (requires `PYPI_API_TOKEN`)
- Dependabot for GitHub Actions and pip
- Issue and pull request templates
- `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`
- Theme asset validation tests
- Ruff linting configuration

### Changed

- **Install**: primary path is `./setup.sh`; hook wrapper pins absolute `cursor-agent-beacon` path
- **Packaging**: themes and GNOME extension bundled in wheel; `cursor-agent-beacon install-*` CLI
- **Privacy**: `CURSOR_AGENT_BEACON_REDACT_CONTENT` hides prompt/response in status
- **GNOME panel**: trusts Python `focused_conversation_id`; file watchers; turn timer; shows tool/denied messages in top bar
- **Bridge**: `stop` hook resolves `stop.gif`; POST body size limit (64 KiB)
- **Sinks**: shared session registry for HTTP-without-file; failure logging
- **Mapper**: `postToolUseFailure` + `permission_denied` → `waiting` / `Denied: {tool}`
- **Stale busy sessions**: decay to `success` after 10 minutes (Python registry + GNOME panel)
- **CI**: ruff format check, pyright, 75% coverage gate, dedicated `setup.sh` smoke job
- **Hooks**: single `SUPPORTED_HOOKS` source of truth
- `postToolUse`, `afterShellExecution`, etc. return `thinking` until `stop`
- `AgentStatus` includes `project` and `label` for panel display

## [0.2.0] - 2026-06-21

### Added

- Local bridge service (`cursor-agent-beacon bridge`)
- `POST /status`, `GET /health`, `GET /status` HTTP endpoints
- Serial writer thread with dry-run mode
- Theme GIF resolution per agent state
- `AgentStatus.from_dict()` for bridge payloads
- Optional `[bridge]` extra with pyserial

## [0.1.0] - 2026-06-21

### Added

- Cursor hook handler with normalized agent states
- Pluggable sinks: log, file, HTTP
- Standard pixel-robot GIF theme (480×480)
- Custom theme layout and loader
- Browser display simulator
- Hook simulation script and unit tests

[Unreleased]: https://github.com/suribe06/cursor-agent-beacon/compare/v0.3.1...HEAD
[0.3.1]: https://github.com/suribe06/cursor-agent-beacon/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/suribe06/cursor-agent-beacon/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/suribe06/cursor-agent-beacon/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/suribe06/cursor-agent-beacon/releases/tag/v0.1.0
