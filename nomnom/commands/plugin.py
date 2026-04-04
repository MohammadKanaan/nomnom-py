from pathlib import Path
from subprocess import CompletedProcess

import typer
from rich.console import Console
from rich.table import Table

from nomnom.config import DEFAULT_PLUGIN_PRIORITY, load_config
from nomnom.discovery import discover_new_plugins, discover_plugins, get_installed_plugin_names
from nomnom.plugin import PluginEntry, has_setup, run_plugin_setup


def run_setups_for_plugins(
    plugins: list[PluginEntry],
) -> None:
    setup_ran = False
    setup_failed = False
    for plugin_name, plugin in plugins:
        if not has_setup(plugin):
            typer.echo(f"Plugin '{plugin_name}' has no setup() method; skipping.")
            continue

        typer.echo(f"Running setup() for plugin '{plugin_name}'...")
        try:
            run_plugin_setup(plugin)
            setup_ran = True
            typer.echo(f"Setup completed for plugin '{plugin_name}'.")
        except KeyboardInterrupt:
            typer.echo(f"Setup cancelled for plugin '{plugin_name}'.")
            raise typer.Exit(1) from None
        except Exception as e:
            typer.echo(f"Setup failed for plugin '{plugin_name}': {e}")
            setup_failed = True

    if not setup_ran:
        typer.echo("No plugin setup was executed.")

    if setup_failed:
        typer.echo("One or more plugin setup steps failed.")
        raise typer.Exit(1)


def _warn_missing_config(config_path: Path, is_error: bool = False) -> None:
    """Helper to warn the user if a configuration file is missing."""
    if not config_path.exists():
        prefix = "Error" if is_error else "Warning"
        typer.echo(f"{prefix}: Configuration file {config_path} not found.")
        if not is_error:
            typer.echo("Run 'nomnom setup' to create one.")


def _update_plugin_in_config(config_path: Path, plugin_name: str, enabled: bool) -> bool:
    """Helper to update the enabled status of a plugin in config.toml."""
    import tomllib

    import tomli_w

    if not config_path.exists():
        return False

    with open(config_path, "rb") as f:
        data = tomllib.load(f)

    plugins = data.setdefault("plugins", [])
    updated = False
    for p in plugins:
        if p.get("name") == plugin_name:
            p["enabled"] = enabled
            updated = True
            break

    if not updated:
        plugins.append(
            {"name": plugin_name, "priority": DEFAULT_PLUGIN_PRIORITY, "enabled": enabled}
        )

    with open(config_path, "wb") as f:
        tomli_w.dump(data, f)

    return True


def _remove_plugin_from_config(config_path: Path, plugin_name: str) -> bool:
    """Helper to remove a plugin from config.toml."""
    import tomllib

    import tomli_w

    if not config_path.exists():
        return False

    with open(config_path, "rb") as f:
        data = tomllib.load(f)

    if "plugins" not in data:
        return False

    original_len = len(data["plugins"])
    data["plugins"] = [p for p in data["plugins"] if p.get("name") != plugin_name]

    if len(data["plugins"]) < original_len:
        with open(config_path, "wb") as f:
            tomli_w.dump(data, f)
        return True

    return False


def _run_package_command(*, action: str, package: str) -> CompletedProcess[str]:
    import subprocess
    import sys

    if action == "install":
        commands = [
            ["uv", "pip", "install", "--python", sys.executable, "--", package],
            [sys.executable, "-m", "pip", "install", package],
        ]
    elif action == "uninstall":
        commands = [
            ["uv", "pip", "uninstall", "--python", sys.executable, package],
            [sys.executable, "-m", "pip", "uninstall", "-y", package],
        ]
    else:
        raise ValueError(f"Unsupported package action: {action}")

    last_error: OSError | None = None
    for command in commands:
        try:
            return subprocess.run(
                command,
                capture_output=True,
                text=True,
            )
        except OSError as e:
            last_error = e

    if last_error is not None:
        raise last_error

    raise RuntimeError("No package command was attempted")


def plugin_add_command(
    *,
    package: str,
    no_setup: bool,
    config_path: Path,
) -> None:
    typer.echo(f"Installing {package}...")
    installed_before = get_installed_plugin_names()

    try:
        result = _run_package_command(action="install", package=package)
    except OSError as e:
        typer.echo(f"Installation failed: could not execute a package installer: {e}")
        raise typer.Exit(1) from e

    if result.returncode != 0:
        typer.echo("Installation failed:")
        error_output = result.stderr or result.stdout
        if error_output:
            typer.echo(error_output.rstrip())
        raise typer.Exit(1)

    typer.echo("Plugin installed successfully.")

    if no_setup:
        typer.echo("Skipping plugin setup (--no-setup).")
        typer.echo("Run 'nomnom watch' to use it.")
        return

    new_plugins = discover_new_plugins(installed_before)

    if not config_path.exists():
        _warn_missing_config(config_path)
    elif new_plugins:
        for name, _ in new_plugins:
            _update_plugin_in_config(config_path, name, enabled=True)
            typer.echo(f"Added plugin '{name}' to {config_path} and enabled it.")

    if not new_plugins:
        typer.echo("No new plugins detected after install; skipping setup.")
        typer.echo("Run 'nomnom watch' to use it.")
        return

    run_setups_for_plugins(new_plugins)
    typer.echo("Run 'nomnom watch' to use it.")


def plugin_remove_command(
    *,
    package: str,
    config_path: Path,
) -> None:
    typer.echo(f"Removing {package}...")
    installed_before = get_installed_plugin_names()

    try:
        result = _run_package_command(action="uninstall", package=package)
    except OSError as e:
        typer.echo(f"Removal failed: could not execute a package installer: {e}")
        raise typer.Exit(1) from e

    if result.returncode != 0:
        typer.echo("Removal failed:")
        error_output = result.stderr or result.stdout
        if error_output:
            typer.echo(error_output.rstrip())
        raise typer.Exit(1)

    typer.echo("Plugin uninstalled successfully.")

    installed_after = get_installed_plugin_names()
    removed_plugins = installed_before - installed_after

    if not config_path.exists():
        _warn_missing_config(config_path)
    else:
        # Also try to remove the package name directly in case the user manually added it
        # and it was never actually installed as a plugin entrypoint.
        names_to_remove = list(removed_plugins)
        if package not in names_to_remove:
            names_to_remove.append(package)

        removed_any = False
        for name in names_to_remove:
            if _remove_plugin_from_config(config_path, name):
                typer.echo(f"Removed plugin '{name}' from {config_path}.")
                removed_any = True

        if not removed_any:
            typer.echo(f"No plugins matching '{package}' were found in {config_path}.")


def plugin_disable_command(
    *,
    plugin_name: str,
    config_path: Path,
) -> None:
    if not config_path.exists():
        _warn_missing_config(config_path, is_error=True)
        raise typer.Exit(1)

    if _update_plugin_in_config(config_path, plugin_name, enabled=False):
        typer.echo(f"Disabled plugin '{plugin_name}' in {config_path}.")
    else:
        typer.echo(f"Failed to update plugin '{plugin_name}' in {config_path}.")


def plugin_enable_command(
    *,
    plugin_name: str,
    config_path: Path,
) -> None:
    if not config_path.exists():
        _warn_missing_config(config_path, is_error=True)
        raise typer.Exit(1)

    if _update_plugin_in_config(config_path, plugin_name, enabled=True):
        typer.echo(f"Enabled plugin '{plugin_name}' in {config_path}.")
    else:
        typer.echo(f"Failed to update plugin '{plugin_name}' in {config_path}.")


def plugin_list_command(
    *,
    config_path: Path,
    console: Console,
) -> None:
    discovered = discover_plugins(rules_path=config_path.parent.resolve() / "rules.toml")
    discovered_names = {name for name, _ in discovered}

    config_plugins = {}
    if config_path.exists():
        try:
            cfg = load_config(config_path)
            for p in cfg.plugins:
                config_plugins[p.name] = p
        except Exception as e:
            console.print(f"[red]Error loading config: {e}[/]")

    all_names = discovered_names.union(config_plugins.keys())

    table = Table(title=f"Available Plugins ({len(all_names)})", show_header=True)
    table.add_column("Name", style="magenta")
    table.add_column("Status", style="bold")
    table.add_column("Priority", justify="right")
    table.add_column("Installed", style="cyan")

    for name in sorted(all_names):
        is_installed = name in discovered_names
        installed_text = "[green]Yes[/]" if is_installed else "[red]No[/]"

        status_text = "[green]Enabled[/]"
        priority_text = "50 (default)"

        if name in config_plugins:
            p_config = config_plugins[name]
            priority_text = str(p_config.priority)
            if not p_config.enabled:
                status_text = "[red]Disabled[/]"

        table.add_row(name, status_text, priority_text, installed_text)

    console.print(table)


def plugin_setup_command(
    *,
    name: str | None,
    all_plugins: bool,
) -> None:
    if name and all_plugins:
        typer.echo("Choose either a plugin name or --all, not both.")
        raise typer.Exit(1)

    if name is None and not all_plugins:
        typer.echo("Provide a plugin name or pass --all.")
        raise typer.Exit(1)

    discovered = discover_plugins()
    if all_plugins:
        run_setups_for_plugins(discovered)
        return

    selected_plugins = [
        PluginEntry(plugin_name, p) for plugin_name, p in discovered if plugin_name == name
    ]
    if not selected_plugins:
        typer.echo(f"Plugin '{name}' was not found.")
        raise typer.Exit(1)

    run_setups_for_plugins(selected_plugins)
