import logging
from pathlib import Path

import typer

from nomnom.config import load_config
from nomnom.discovery import discover_plugins, prioritize_plugins

app = typer.Typer(help="Plugin-based file watcher CLI")


@app.command()
def watch(
    config: Path = typer.Option(
        "config.toml",
        "--config",
        "-c",
        help="Path to TOML config file",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose logging",
    ),
) -> None:
    """Watch configured folders and dispatch events to plugins."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(name)s — %(levelname)s — %(message)s",
    )

    cfg = load_config(config)

    raw_plugins = discover_plugins()
    plugins = prioritize_plugins(raw_plugins, cfg)

    typer.echo(f"Loaded {len(plugins)} plugin(s):")
    for name, _ in plugins:
        typer.echo(f"  - {name}")

    typer.echo(f"Watching {len(cfg.watch_groups)} folder group(s):")
    for wg in cfg.watch_groups:
        typer.echo(f"  - {wg.name}: {', '.join(str(p) for p in wg.paths)}")


if __name__ == "__main__":
    app()
