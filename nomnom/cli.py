from pathlib import Path
from typing import Annotated

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
    once_watch_group: Annotated[
        str | None,
        typer.Argument(
            metavar="[WATCH_GROUP]",
            help="Watch group name to process in --once mode",
        ),
    ] = None,
    config: Annotated[
        Path,
        typer.Option(
            "--config",
            "-c",
            help="Path to TOML config file",
        ),
    ] = Path("config.toml"),
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Enable verbose logging",
        ),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry",
            "--dry-run",
            help="Show effects without executing",
        ),
    ] = False,
    once: Annotated[
        bool,
        typer.Option(
            "--once",
            help="Process existing files once and exit",
        ),
    ] = False,
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
    config: Annotated[
        Path,
        typer.Option(
            "--config",
            "-c",
            help="Path to TOML config file",
        ),
    ] = Path("config.toml"),
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
    package: Annotated[str, typer.Argument(help="Package name or git URL")],
    no_setup: Annotated[
        bool,
        typer.Option(
            "--no-setup",
            help="Skip interactive plugin setup",
        ),
    ] = False,
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
    name: Annotated[
        str | None,
        typer.Argument(
            help="Plugin name to run setup for",
        ),
    ] = None,
    all_plugins: Annotated[
        bool,
        typer.Option(
            "--all",
            help="Run setup for all discovered plugins",
        ),
    ] = False,
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
