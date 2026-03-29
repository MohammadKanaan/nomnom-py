# nomnom

**nomnom** consists of a file watcher core that fires events, and a plugin ecosystem that handles effects.
You can install plugins, make your own, or use the built-in rules plugin for simpler flows.

## Quick Start

**1. Install**

```bash
pip install nomnom
```

**2. Initialize**
Generates a default `config.toml` in your project root.

```bash
nomnom setup
```

**3. Watch**
Starts watching your directories based on the configuration.

```bash
nomnom watch
```

## Configuration

Configure your watchers and plugins in `config.toml` (or pass `--config <path>`).

```toml
# Watch all files in the archive folder
[[watch]]
name = "archive"
paths = ["./archive"]

# Watch only specific extensions in the inbox
[[watch]]
name = "inbox"
paths = ["./inbox"]
extensions = [".pdf", ".txt"] 

# Enable and prioritize plugins (lower runs first)
[[plugins]]
name = "nomnom-plugin-rules"
priority = 10
enabled = true
```

## Plugins

### The Built-in Rules Plugin

Declarative file-event rules driven by a `rules.toml` file — no code required.
See [`plugins/nomnom-plugin-rules/README.md`](plugins/nomnom-plugin-rules/README.md) for the rule format and options.

### Installing Community Plugins

You can install plugins from PyPl or GitHub

```bash
nomnom plugin add <name/git-link>
```

Example:

```bash
nomnom plugin add git+https://github.com/MohammadKanaan/nomnom-obsidian-transcribe
```

### Develop Your Own

Quick start by scaffolding a local, auto-discoverable plugin:

```bash
nomnom plugin create <name>
```

#### Manual Development

A plugin should expose a class implementing `Plugin` (and optionally `SetupPlugin`). Return `Effect` subclasses to act on the filesystem:

```python
from nomnom import Plugin, FileEvent, Effect

class MyPlugin(Plugin):
    def matches(self, event: FileEvent) -> bool:
        return event.path.suffix == ".txt"

    def handle(self, event: FileEvent) -> list[Effect]:
        return []  # Return your effects here
```

Register the class via an entry point in `pyproject.toml`:

```toml
[project.entry-points."nomnom.plugins"]
my-plugin = "my_package:MyPlugin"
```

*Install the package and add it to your config with `nomnom plugin add <package>`.*

## CLI Reference

```text
Core Commands:
  nomnom watch [GROUP] [OPTS]   Start watching (Opts: -c/--config, -v/--verbose, --dry-run, --once)
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