import logging
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from nomnom.config import load_config
from nomnom.discovery import discover_plugins, prioritize_plugins
from nomnom.watcher import run_watcher

app = typer.Typer(help="Plugin-based file watcher CLI")
console = Console()


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
    # Suppress watchfiles debug messages unless verbose
    if not verbose:
        logging.getLogger("watchfiles").setLevel(logging.WARNING)

    cfg = load_config(config)

    raw_plugins = discover_plugins()
    plugins = prioritize_plugins(raw_plugins, cfg)

    # Banner
    banner = Panel(
        "[bold cyan]nomnom[/] v0.1.0\n"
        f"[dim]Config: {config}[/]",
        border_style="cyan",
    )
    console.print(banner)

    # Plugins table
    plugin_table = Table(title=f"Plugins ({len(plugins)})", show_header=len(plugins) > 0)
    plugin_table.add_column("Name", style="magenta")
    plugin_table.add_column("Priority", justify="right", style="dim")
    for name, _ in plugins:
        priority_map = {p.name: p.priority for p in cfg.plugins}
        priority = priority_map.get(name, 50)
        plugin_table.add_row(name, str(priority))
    console.print(plugin_table)

    # Watch groups table
    watch_table = Table(title=f"Watch Groups ({len(cfg.watch_groups)})")
    watch_table.add_column("Name", style="green")
    watch_table.add_column("Paths", style="dim")
    for wg in cfg.watch_groups:
        watch_table.add_row(wg.name, ", ".join(str(p) for p in wg.paths))
    console.print(watch_table)

    console.print("\n[dim]Watching for changes... (Ctrl+C to stop)[/]\n")

    run_watcher(cfg, plugins, console)


if __name__ == "__main__":
    app()
