# Contributing to Cursor Agent Beacon

Thanks for your interest in contributing. This project is intentionally small and focused: **deterministic agent status from Cursor hooks**, with optional hardware display later.

## Ways to contribute

- Bug reports and feature requests via [GitHub Issues](https://github.com/suribe06/cursor-agent-beacon/issues)
- Pull requests for fixes, tests, docs, themes, or bridge improvements
- Sharing custom themes (locally — do not commit copyrighted assets)
- ESP32 firmware work (Phase 3) when hardware is available

## Development setup

End users can run `./setup.sh` from a clone (creates `.venv` and installs hooks).

For package development:

```bash
git clone https://github.com/suribe06/cursor-agent-beacon.git
cd cursor-agent-beacon

python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,bridge]"
```

Or use `./setup.sh` then `pip install -e ".[dev]"` for extra dev tools on top of the user install.

## Running checks locally

```bash
pytest -m "not smoke"    # unit tests (smoke runs pip install via setup.sh)
pytest -m smoke          # optional: end-to-end ./setup.sh
ruff check src tests
ruff format --check src tests
pyright
python -m build
```

Auto-fix lint issues:

```bash
ruff check --fix src tests
ruff format src tests
```

Simulate hooks without Cursor:

```bash
python3 scripts/simulate_hook.py examples/sample-events/after_agent_thought.json
cursor-agent-beacon bridge
```

## Pull request guidelines

1. **Keep scope focused** — one logical change per PR when possible
2. **Add tests** for behavior changes
3. **Update docs** if users need to know about the change
4. **Run CI checks locally** before opening the PR
5. **Follow existing code style** — ruff enforces formatting and imports

## Project layout

| Path | Purpose |
| --- | --- |
| `src/cursor_agent_beacon/` | Python package (hooks, bridge, themes) |
| `tests/` | Unit and integration tests |
| `themes/standard/` | Bundled GIF theme |
| `themes/custom/` | Personal themes (gitignored) |
| `.cursor/hooks/` | Cursor hook entry point |
| `docs/` | Documentation |
| `scripts/` | Simulation and asset export |

## Commit messages

Use clear, imperative messages. Conventional prefixes are welcome but not required:

- `fix:` bug fix
- `feat:` new feature
- `docs:` documentation only
- `test:` tests only
- `ci:` CI / tooling

## Code of conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md). Be respectful and constructive.

## Questions

Open a [Discussion](https://github.com/suribe06/cursor-agent-beacon/discussions) or an issue if you are unsure whether a change fits the project scope.
