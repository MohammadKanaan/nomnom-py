# AGENTS.md

## Project Overview

**nomnom** is a plugin-based file watcher CLI. It watches directories for file changes and dispatches events to plugins that perform filesystem operations.

- **Entry point:** `nomnom/cli.py` (Typer app)
- **Package:** `nomnom/`
- **Tests:** `tests/`
- **Built-in plugin:** `plugins/nomnom-plugin-rules/`

## Tech Stack

- Python 3.11+ (use modern syntax: `match/case`, `X | Y` unions, dataclasses)
- CLI: `typer`
- File watching: `watchfiles`
- Build: `hatchling`
- Deps: `uv`

## Code Style

- **Linter:** ruff — rules: E, F, W, I, UP, B, SIM. Line length: 100.
- **Type checker:** mypy — strict mode enabled, target Python 3.11.
- Prefer `Protocol` over ABC for plugin interfaces.
- Use `dataclass` for data types (effects, events).
- Use `TYPE_CHECKING` guards to avoid circular imports.

## Testing

- Framework: `pytest`
- Run: `uv run pytest`
- Test files: `tests/test_<module>.py`
- Fixtures in `tests/conftest.py` (e.g. `make_event`, `StubPlugin`)

## Commits

- Keep commits minimal; describe the overview of changes.
- Prefix with one of: `feat:`, `fix:`, `test:`, `refactor:`

## Architecture

- **Event-driven:** `watchfiles` detects changes → `FileEvent` objects are created.
- **Plugin protocol:** plugins implement `matches(event)` and `handle(event)`.
- **Effect system:** plugins return `Effect` objects (`MoveFile`, `DeleteFile`, `CreateFile`, `EditFile`, `EmitEvent`).
- **Dispatcher:** routes events to matching plugins with depth-limited recursion for `EmitEvent`.
- **Executor:** performs atomic file operations (tempfile + rename).
- **Discovery:** plugins are loaded via Python entry points.
- **Config:** TOML-based (`config.toml`) with watch groups and plugin settings.

## Key Commands

```sh
uv run pytest              # run tests
uv run ruff check .        # lint
uv run mypy nomnom         # typecheck
uv run nomnom --help       # CLI help
```
