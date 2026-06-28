# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **GNOME status panel** (v0.10 pre-release): `gnome-extension/` + install scripts
- **Multi-session file sink**: `registry.json`, `sessions/<id>.json`, auto-focused `status.json`
- `scripts/install-desktop.sh`, `install-user-hooks.sh`, `install-gnome-panel.sh`
- `docs/gnome-panel.md`
- Session registry (`session_registry.py`) with per-conversation status and busy-session focus

### Changed

- Mapper: `postToolUse`, `afterShellExecution`, etc. return `thinking` until `stop` (not premature `success`)
- `AgentStatus` includes `project` and `label` for panel display

### Added (infra)
- Release workflow on version tags
- Dependabot for GitHub Actions and pip
- Issue and pull request templates
- `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`
- Theme asset validation tests
- Ruff linting configuration

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
- Standard pixel-robot GIF theme (240×240)
- Custom theme layout and loader
- Browser display simulator
- Hook simulation script and unit tests

[Unreleased]: https://github.com/suribe06/cursor-agent-beacon/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/suribe06/cursor-agent-beacon/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/suribe06/cursor-agent-beacon/releases/tag/v0.1.0
