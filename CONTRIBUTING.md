# Contributing

## Development Setup

```bash
uv sync --dev
```

This installs the project and the development toolchain into the local virtual environment managed by `uv`.

## Common Commands

```bash
uv run pytest
uv run ruff check
uv run mypy
```

Run the full test suite before opening a pull request. If you change CLI behavior, also verify:

```bash
uv run nomnom --help
```

## Working on Plugins

Use the built-in scaffold to create a local plugin package:

```bash
uv run nomnom plugin create my-plugin
```

Local plugins live under `plugins/`. The built-in `rules` plugin is implemented in `nomnom.builtin.rules`.

## Pull Requests

- Keep changes focused and minimal.
- Add or update tests for behavior changes.
- Update docs or examples when public-facing behavior changes.
- Prefer small commits with clear messages.
