import os
from pathlib import Path

import typer
from rich.console import Console

from nomnom.cli_commands import (
    plugin_add_command,
    plugin_disable_command,
    plugin_enable_command,
    plugin_list_command,
    plugin_remove_command,
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

DEFAULT_CONFIG = os.environ.get("NOMNOM_CONFIG", "config.toml")

app = typer.Typer(
    help="Plugin-based file watcher CLI",
    context_settings={"help_option_names": ["-h", "--help"]},
)
plugin_app = typer.Typer(
    help="Manage plugins",
    context_settings={"help_option_names": ["-h", "--help"]},
)
app.add_typer(plugin_app, name="plugin")
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
        DEFAULT_CONFIG,
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
        DEFAULT_CONFIG,
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


@plugin_app.command("add")
def plugin_add(
    package: str = typer.Argument(help="Package name or git URL"),
    no_setup: bool = typer.Option(
        False,
        "--no-setup",
        help="Skip interactive plugin setup",
    ),
    config: Path = typer.Option(
        DEFAULT_CONFIG,
        "--config",
        "-c",
        help="Path to TOML config file",
    ),
) -> None:
    """Install and add a plugin to configuration."""
    plugin_add_command(
        package=package,
        no_setup=no_setup,
        config_path=config,
        get_installed_plugin_names_fn=get_installed_plugin_names,
        discover_new_plugins_fn=discover_new_plugins,
        run_setups_for_plugins_fn=lambda plugins: run_setups_for_plugins(
            plugins,
            has_setup_fn=has_setup,
            run_plugin_setup_fn=run_plugin_setup,
        ),
    )


@plugin_app.command("remove")
def plugin_remove(
    package: str = typer.Argument(help="Plugin package name to remove"),
    config: Path = typer.Option(
        DEFAULT_CONFIG,
        "--config",
        "-c",
        help="Path to TOML config file",
    ),
) -> None:
    """Remove a plugin package and from configuration."""
    plugin_remove_command(
        package=package,
        config_path=config,
        get_installed_plugin_names_fn=get_installed_plugin_names,
    )


@plugin_app.command("disable")
def plugin_disable(
    plugin_name: str = typer.Argument(help="Plugin name to disable"),
    config: Path = typer.Option(
        DEFAULT_CONFIG,
        "--config",
        "-c",
        help="Path to TOML config file",
    ),
) -> None:
    """Disable a plugin in configuration."""
    plugin_disable_command(
        plugin_name=plugin_name,
        config_path=config,
    )


@plugin_app.command("enable")
def plugin_enable(
    plugin_name: str = typer.Argument(help="Plugin name to enable"),
    config: Path = typer.Option(
        DEFAULT_CONFIG,
        "--config",
        "-c",
        help="Path to TOML config file",
    ),
) -> None:
    """Enable a plugin in configuration."""
    plugin_enable_command(
        plugin_name=plugin_name,
        config_path=config,
    )


@plugin_app.command("list")
def plugin_list(
    config: Path = typer.Option(
        DEFAULT_CONFIG,
        "--config",
        "-c",
        help="Path to TOML config file",
    ),
) -> None:
    """List all available plugins and their status."""
    plugin_list_command(
        config_path=config,
        console=console,
        load_config_fn=load_config,
        discover_plugins_fn=discover_plugins,
    )


@plugin_app.command("setup")
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
