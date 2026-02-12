from pathlib import Path

import typer
from rich.console import Console

from nomnom.cli_commands import (
    plugin_install_command,
    plugin_setup_command,
    run_setups_for_plugins,
    setup_command,
    watch_command,
)
from nomnom.config import load_config
from nomnom.create_plugin import create_plugin
from nomnom.discovery import (
    discover_new_plugins,
    discover_plugins,
    get_installed_plugin_names,
    prioritize_plugins,
)
from nomnom.plugin import has_setup, run_plugin_setup
from nomnom.watcher import run_watcher

app = typer.Typer(
    help="Plugin-based file watcher CLI",
    context_settings={"help_option_names": ["-h", "--help"]},
)
console = Console()

app.command("create-plugin")(create_plugin)


@app.command()
def watch(
    once_watch_group: str | None = typer.Argument(
        None,
        metavar="[WATCH_GROUP]",
        help="Watch group name to process in --once mode",
    ),
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
    dry_run: bool = typer.Option(
        False,
        "--dry",
        "--dry-run",
        help="Show effects without executing",
    ),
    once: bool = typer.Option(
        False,
        "--once",
        help="Process existing files once and exit",
    ),
) -> None:
    """Watch configured folders and dispatch events to plugins."""
    watch_command(
        once_watch_group=once_watch_group,
        config=config,
        verbose=verbose,
        dry_run=dry_run,
        once=once,
        console=console,
        load_config_fn=load_config,
        discover_plugins_fn=discover_plugins,
        prioritize_plugins_fn=prioritize_plugins,
        run_watcher_fn=run_watcher,
    )


@app.command()
def setup(
    config: Path = typer.Option(
        "config.toml",
        "--config",
        "-c",
        help="Path to TOML config file",
    ),
) -> None:
    """Interactive setup to create or update configuration."""
    setup_command(
        config=config,
        console=console,
        load_config_fn=load_config,
        discover_plugins_fn=discover_plugins,
    )


@app.command()
def plugin_install(
    package: str = typer.Argument(help="Package name or git URL"),
    no_setup: bool = typer.Option(
        False,
        "--no-setup",
        help="Skip interactive plugin setup",
    ),
) -> None:
    """Install a plugin package."""
    plugin_install_command(
        package=package,
        no_setup=no_setup,
        get_installed_plugin_names_fn=get_installed_plugin_names,
        discover_new_plugins_fn=discover_new_plugins,
        run_setups_for_plugins_fn=lambda plugins: run_setups_for_plugins(
            plugins,
            has_setup_fn=has_setup,
            run_plugin_setup_fn=run_plugin_setup,
        ),
    )


@app.command("plugin-setup")
def plugin_setup(
    name: str | None = typer.Argument(
        None,
        help="Plugin name to run setup for",
    ),
    all_plugins: bool = typer.Option(
        False,
        "--all",
        help="Run setup for all discovered plugins",
    ),
) -> None:
    """Run setup() for one plugin or all discovered plugins."""
    plugin_setup_command(
        name=name,
        all_plugins=all_plugins,
        discover_plugins_fn=discover_plugins,
        run_setups_for_plugins_fn=lambda plugins: run_setups_for_plugins(
            plugins,
            has_setup_fn=has_setup,
            run_plugin_setup_fn=run_plugin_setup,
        ),
    )


if __name__ == "__main__":
    app()
