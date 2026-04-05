# nomnom

[![CI](https://github.com/MohammadKanaan/nomnom-py/actions/workflows/ci.yml/badge.svg)](https://github.com/MohammadKanaan/nomnom-py/actions/workflows/ci.yml)
[![PyPI Version](https://img.shields.io/pypi/v/nomnom-py)](https://pypi.org/project/nomnom-py/)
[![Python Versions](https://img.shields.io/pypi/pyversions/nomnom-py)](https://pypi.org/project/nomnom-py/)

`nomnom` is an extensible file watcher for local automation. The core detects file changes and fires events. Plugins do the actual work: moving files, enriching them, or kicking off downstream workflows.

## Install

With `uv`:

```bash
uv tool install nomnom-py
```

With `pip`:

```bash
pip install nomnom-py
```

## Quick Start

### Initialize

Generates a default `config.toml` in your project root.
If you use the built-in `rules` plugin, keep `rules.toml` in that same directory so `nomnom` can read both files together.

```bash
nomnom setup
```

### Watch

Starts watching your directories based on the configuration.

```bash
nomnom watch
```

Use `nomnom watch --once <group>` to process a single watch group one time, or `nomnom watch --dry` to inspect behavior without applying file effects.

## Example Configuration

`nomnom` reads `config.toml` from the current project by default, or a custom path passed with `--config`.
When the built-in `rules` plugin is enabled, `nomnom` also reads `rules.toml` from that same directory.

```toml
[[watch]]
name = "inbox"
paths = ["./fixtures/inbox"]
include = ["*.pdf", "*.txt"]

[[watch]]
name = "archive"
paths = ["./fixtures/archive"]

[[plugins]]
name = "rules"
priority = 10
enabled = true
```

For a fuller starter file, see [`config.example.toml`](config.example.toml).

## Plugins

### The Built-in Rules Plugin

A rules plugin for declarative file automation driven by `rules.toml`.
It ships with the main `nomnom-py` install and is configured as `rules`.
Keep `config.toml` and `rules.toml` side by side. If you run `nomnom --config /path/to/config.toml`, the built-in plugin will read `/path/to/rules.toml` automatically.
See [`RULES.md`](RULES.md) for the rule format and supported actions, and
[`rules.example.toml`](rules.example.toml) for a starter example.

### Installing Community Plugins

Plugins can be installed from PyPI or directly from a Git repository:

```bash
nomnom plugin add <package-name-or-git-url>
```

Example:

```bash
nomnom plugin add git+https://github.com/<owner>/nomnom-plugin-example
```

### Creating a Plugin

Scaffold a local plugin package inside `plugins/`:

```bash
nomnom plugin create <name>
```

The generated package includes a `pyproject.toml` entry point and a stub plugin module. Local plugins are automatically discoverable, no need to configure them.

If you'd like to publish your plugin, move it to its own repo and publish it to GitHub or PyPI. There is no system for discovering plugins yet but shoot me an email if interested.

### Plugin API

Plugins implement two methods:

```python
def matches(self, event: FileEvent) -> bool: ...
def handle(self, event: FileEvent) -> list[Effect]: ...
```

#### `FileEvent`

| Field | Type | Description |
|-------|------|-------------|
| `event_type` | `EventType` | `EventType.CREATED`, `MODIFIED`, or `DELETED` |
| `path` | `Path` | Absolute path to the changed file |
| `watch_group` | `str` | Name of the watch group that triggered this event |
| `created_at` | `datetime` | UTC timestamp when the event was created |

#### Effects

`handle()` returns a list of zero or more `Effect` values. The dispatcher executes them in order.

| Effect | Fields | Description |
|--------|--------|-------------|
| `MoveFile` | `source: Path`, `destination: Path`, `overwrite: bool = True` | Moves a file. Creates parent directories as needed. Skipped if source is missing; skipped (or overwrites) if destination exists based on `overwrite`. |
| `DeleteFile` | `path: Path` | Deletes a file. Skipped if the file does not exist. |
| `CreateFile` | `path: Path`, `content: bytes` | Creates a file with the given content, creating parent directories as needed. |
| `EditFile` | `path: Path`, `action: EditAction`, `content: bytes` | Prepends or appends `content` to an existing file. `action` is `EditAction.PREPEND` or `EditAction.APPEND`. |
| `EmitEvent` | `event: FileEvent` | Injects a new `FileEvent` back into the dispatcher. Useful for chaining logic across plugins. Depth is capped at 10 to prevent infinite loops. |

## Development

```bash
uv sync --dev
uv run pytest
uv run ruff check
uv run mypy nomnom
```

Contributor guidance lives in [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Dependencies

`nomnom` is built with these open-source libraries:

- [rich](https://github.com/Textualize/rich) — MIT License
- [typer](https://github.com/tiangolo/typer) — MIT License
- [watchfiles](https://github.com/samuelcolvin/watchfiles) — MIT License
- [tomli-w](https://github.com/hcloskey/tomli-w) — BSD-3-Clause License

Dev dependencies:

- [pytest](https://github.com/pytest-dev/pytest) — MIT License
- [pytest-cov](https://github.com/pytest-dev/pytest-cov) — MIT License
- [ruff](https://github.com/astral-sh/ruff) — MIT License
- [mypy](https://github.com/python/mypy) — MIT License


## CLI Reference

```text
Core Commands:
  nomnom watch [WATCH_GROUP] [OPTS]  Start watching (Opts: -c/--config, -V/--verbose, --dry-run, --once)
  nomnom setup [OPTS]           Create or update the config file
  nomnom --version / -v         Print installed version

Plugin Management:
  nomnom plugin add PACKAGE     Install and register a plugin
  nomnom plugin remove PACKAGE  Remove a plugin
  nomnom plugin enable NAME     Enable a plugin in config
  nomnom plugin disable NAME    Disable a plugin in config
  nomnom plugin list            List active plugins
  nomnom plugin setup           Run setup for specific/all plugins
  nomnom plugin create NAME     Scaffold a new local plugin
```
