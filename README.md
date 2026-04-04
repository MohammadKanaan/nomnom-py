# nomnom

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

## Development

```bash
uv sync --dev
uv run pytest
uv run ruff check
uv run mypy nomnom
```

Contributor guidance lives in [`CONTRIBUTING.md`](CONTRIBUTING.md).


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
