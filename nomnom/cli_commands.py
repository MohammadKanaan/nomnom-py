import logging
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from nomnom.config import DEFAULT_PLUGIN_PRIORITY, Config
from nomnom.plugin import Plugin


class RunWatcherProtocol(Protocol):
    def __call__(
        self,
        config: Config,
        plugins: list[tuple[str, Plugin]],
        console: Console,
        *,
        dry_run: bool,
        once: bool,
        once_watch_group: str | None,
    ) -> None: ...


def run_setups_for_plugins(
    plugins: list[tuple[str, Plugin]],
    *,
    has_setup_fn: Callable[[Plugin], bool],
    run_plugin_setup_fn: Callable[[Plugin], None],
) -> None:
    setup_ran = False
    setup_failed = False
    for plugin_name, plugin in plugins:
        if not has_setup_fn(plugin):
            typer.echo(f"Plugin '{plugin_name}' has no setup() method; skipping.")
            continue

        typer.echo(f"Running setup() for plugin '{plugin_name}'...")
        try:
            run_plugin_setup_fn(plugin)
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


def watch_command(
    *,
    once_watch_group: str | None,
    config: Path,
    verbose: bool,
    dry_run: bool,
    once: bool,
    console: Console,
    load_config_fn: Callable[[Path], Config],
    discover_plugins_fn: Callable[[], list[tuple[str, Plugin]]],
    prioritize_plugins_fn: Callable[[list[tuple[str, Plugin]], Config], list[tuple[str, Plugin]]],
    run_watcher_fn: RunWatcherProtocol,
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(name)s — %(levelname)s — %(message)s",
        handlers=[
            RichHandler(
                console=console,
                show_time=False,
                show_path=False,
                markup=True,
            )
        ],
        force=True,
    )
    if not verbose:
        logging.getLogger("watchfiles").setLevel(logging.WARNING)

    if not config.exists():
        setup_cmd = "nomnom setup"
        if config != Path("config.toml"):
            setup_cmd += f" --config {config}"
        console.print(
            f"[red]Config file not found: {config}[/]\n"
            f"[yellow]Run `{setup_cmd}` to create one.[/]"
        )
        raise typer.Exit(code=1)

    cfg = load_config_fn(config)
    if once_watch_group and not once:
        console.print("[red]Watch group argument is only supported with --once.[/]")
        raise typer.Exit(code=1)

    if once and once_watch_group:
        available_groups = {group.name for group in cfg.watch_groups}
        if once_watch_group not in available_groups:
            available = ", ".join(sorted(available_groups)) if available_groups else "(none)"
            console.print(
                f"[red]Watch group not found: {once_watch_group}[/]\n"
                f"[yellow]Available groups: {available}[/]"
            )
            raise typer.Exit(code=1)

    raw_plugins = discover_plugins_fn()
    prioritized_plugins = prioritize_plugins_fn(raw_plugins, cfg)

    config_plugin_status = {p.name: p.enabled for p in cfg.plugins}
    plugins = [
        (name, plugin)
        for name, plugin in prioritized_plugins
        if config_plugin_status.get(name, True)
    ]

    banner = Panel(
        "[bold cyan]nomnom[/] v0.1.0\n"
        f"[dim]Config: {config}[/]"
        + ("\n[bold yellow][DRY RUN][/bold yellow]" if dry_run else ""),
        border_style="cyan",
    )
    console.print(banner)

    plugin_table = Table(title=f"Plugins ({len(plugins)})", show_header=len(plugins) > 0)
    plugin_table.add_column("Name", style="magenta")
    plugin_table.add_column("Priority", justify="right", style="dim")
    priority_map = {p.name: p.priority for p in cfg.plugins}
    for name, _ in plugins:
        priority = priority_map.get(name, 50)
        plugin_table.add_row(name, str(priority))
    console.print(plugin_table)

    watch_table = Table(title=f"Watch Groups ({len(cfg.watch_groups)})")
    watch_table.add_column("Name", style="green")
    watch_table.add_column("Paths", style="dim")
    watch_table.add_column("Filters", style="dim")
    for wg in cfg.watch_groups:
        filters: list[str] = []
        if wg.include:
            filters.append(f"include={','.join(wg.include)}")
        if wg.exclude:
            filters.append(f"exclude={','.join(wg.exclude)}")
        watch_table.add_row(
            wg.name,
            ", ".join(str(p) for p in wg.paths),
            "; ".join(filters) if filters else "-",
        )
    console.print(watch_table)

    if once:
        if once_watch_group:
            console.print(
                f"\n[dim]One-shot mode: scanning existing files in group "
                f"'{once_watch_group}'...[/]\n"
            )
        else:
            console.print("\n[dim]One-shot mode: scanning existing files...[/]\n")
    elif dry_run:
        console.print("\n[dim]Dry-run mode: showing effects without executing...[/]\n")
    else:
        console.print("\n[dim]Watching for changes... (Ctrl+C to stop)[/]\n")

    run_watcher_fn(
        cfg,
        plugins,
        console,
        dry_run=dry_run,
        once=once,
        once_watch_group=once_watch_group,
    )


def setup_command(
    *,
    config: Path,
    console: Console,
    load_config_fn: Callable[[Path], Config],
    discover_plugins_fn: Callable[[], list[tuple[str, Plugin]]],
) -> None:
    import tomli_w

    console.print(
        Panel(
            "[bold cyan]nomnom Setup Wizard[/]\n"
            "[dim]Configure your file watcher interactively[/]",
            border_style="cyan",
        )
    )

    if config.exists():
        console.print(f"\n[yellow]Found existing config at {config}[/]")
        if not Confirm.ask("Do you want to edit it?", default=True):
            console.print("[dim]Setup cancelled.[/]")
            return

        try:
            cfg = load_config_fn(config)
            existing_watch_groups = [
                {
                    "name": wg.name,
                    "paths": [str(p) for p in wg.paths],
                    "include": wg.include,
                    "exclude": wg.exclude,
                }
                for wg in cfg.watch_groups
            ]
            existing_plugins = [
                {"name": p.name, "priority": p.priority, "enabled": p.enabled}
                for p in cfg.plugins
            ]
        except Exception as e:
            console.print(f"[red]Error loading config: {e}[/]")
            existing_watch_groups = []
            existing_plugins = []
    else:
        console.print(f"\n[green]Creating new config at {config}[/]")
        existing_watch_groups = []
        existing_plugins = []

    console.print("\n[bold]Watch Groups Configuration[/]")
    watch_groups = []

    if existing_watch_groups:
        console.print("[dim]Existing watch groups:[/]")
        for i, wg in enumerate(existing_watch_groups, 1):
            console.print(f"  {i}. [green]{wg['name']}[/]: {', '.join(wg['paths'])}")

        if Confirm.ask("Keep existing watch groups?", default=True):
            watch_groups.extend(existing_watch_groups)

    if Confirm.ask("Add new watch group?", default=not watch_groups):
        while True:
            name = Prompt.ask("Watch group name")
            paths_input = Prompt.ask("Paths to watch (comma-separated)")
            paths = [p.strip() for p in paths_input.split(",") if p.strip()]
            include_input = Prompt.ask(
                "Include patterns (comma-separated, optional)", default=""
            )
            exclude_input = Prompt.ask(
                "Exclude patterns (comma-separated, optional)", default=""
            )
            include = [p.strip() for p in include_input.split(",") if p.strip()]
            exclude = [p.strip() for p in exclude_input.split(",") if p.strip()]

            watch_groups.append(
                {
                    "name": name,
                    "paths": paths,
                    "include": include,
                    "exclude": exclude,
                }
            )

            if not Confirm.ask("Add another watch group?", default=False):
                break

    if not watch_groups:
        console.print("[red]Error: At least one watch group is required![/]")
        return

    console.print("\n[bold]Plugins Configuration[/]")
    discovered = discover_plugins_fn()

    if discovered:
        console.print(f"\n[dim]Discovered {len(discovered)} plugin(s):[/]")
        for plugin_name, _ in discovered:
            console.print(f"  • [magenta]{plugin_name}[/]")

    plugins = []

    if existing_plugins:
        console.print("\n[dim]Existing plugin configurations:[/]")
        for i, plugin in enumerate(existing_plugins, 1):
            console.print(
                f"  {i}. [magenta]{plugin['name']}[/] (priority: {plugin['priority']})"
            )

        if Confirm.ask("Keep existing plugin configurations?", default=True):
            plugins.extend(existing_plugins)

    if Confirm.ask("Configure plugins?", default=not plugins):
        available_plugins = [name for name, _ in discovered]

        while True:
            if available_plugins:
                console.print("\n[dim]Available plugins:[/]")
                for plugin_name in available_plugins:
                    console.print(f"  • {plugin_name}")

            name = Prompt.ask("Plugin name")
            priority = int(
                Prompt.ask(
                    "Priority (lower = higher priority)", default=str(DEFAULT_PLUGIN_PRIORITY)
                )
            )
            plugins.append({"name": name, "priority": priority, "enabled": True})

            if not Confirm.ask("Configure another plugin?", default=False):
                break

    config_data = {"watch": watch_groups, "plugins": plugins}

    try:
        with open(config, "wb") as f:
            tomli_w.dump(config_data, f)
        console.print(f"\n[bold green]✓[/] Configuration saved to {config}")

        summary = Table(title="Configuration Summary")
        summary.add_column("Section", style="cyan")
        summary.add_column("Details", style="dim")
        summary.add_row("Watch Groups", str(len(watch_groups)))
        summary.add_row("Plugins", str(len(plugins)))
        console.print(summary)

    except Exception as e:
        console.print(f"[red]Error saving config: {e}[/]")


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
            {
                "name": plugin_name,
                "priority": DEFAULT_PLUGIN_PRIORITY,
                "enabled": enabled,
            }
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


def plugin_add_command(
    *,
    package: str,
    no_setup: bool,
    config_path: Path,
    get_installed_plugin_names_fn: Callable[[], set[str]],
    discover_new_plugins_fn: Callable[[set[str]], list[tuple[str, Plugin]]],
    run_setups_for_plugins_fn: Callable[[list[tuple[str, Plugin]]], None],
) -> None:
    import subprocess
    import sys

    typer.echo(f"Installing {package}...")
    installed_before = get_installed_plugin_names_fn()
    install_cmd = ["uv", "pip", "install", "--python", sys.executable, "--", package]

    try:
        result = subprocess.run(
            install_cmd,
            capture_output=True,
            text=True,
        )
    except OSError as e:
        typer.echo(f"Installation failed: could not execute '{install_cmd[0]}': {e}")
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

    new_plugins = discover_new_plugins_fn(installed_before)

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

    run_setups_for_plugins_fn(new_plugins)
    typer.echo("Run 'nomnom watch' to use it.")


def plugin_remove_command(
    *,
    package: str,
    config_path: Path,
    get_installed_plugin_names_fn: Callable[[], set[str]],
) -> None:
    import subprocess
    import sys

    typer.echo(f"Removing {package}...")
    installed_before = get_installed_plugin_names_fn()
    uninstall_cmd = ["uv", "pip", "uninstall", "--python", sys.executable, package]

    try:
        result = subprocess.run(
            uninstall_cmd,
            capture_output=True,
            text=True,
        )
    except OSError as e:
        typer.echo(f"Removal failed: could not execute '{uninstall_cmd[0]}': {e}")
        raise typer.Exit(1) from e

    if result.returncode != 0:
        typer.echo("Removal failed:")
        error_output = result.stderr or result.stdout
        if error_output:
            typer.echo(error_output.rstrip())
        raise typer.Exit(1)

    typer.echo("Plugin uninstalled successfully.")

    installed_after = get_installed_plugin_names_fn()
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
    load_config_fn: Callable[[Path], Config],
    discover_plugins_fn: Callable[[], list[tuple[str, Plugin]]],
) -> None:
    discovered = discover_plugins_fn()
    discovered_names = {name for name, _ in discovered}

    config_plugins = {}
    if config_path.exists():
        try:
            cfg = load_config_fn(config_path)
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
    discover_plugins_fn: Callable[[], list[tuple[str, Plugin]]],
    run_setups_for_plugins_fn: Callable[[list[tuple[str, Plugin]]], None],
) -> None:
    if name and all_plugins:
        typer.echo("Choose either a plugin name or --all, not both.")
        raise typer.Exit(1)

    if name is None and not all_plugins:
        typer.echo("Provide a plugin name or pass --all.")
        raise typer.Exit(1)

    discovered = discover_plugins_fn()
    if all_plugins:
        run_setups_for_plugins_fn(discovered)
        return

    selected_plugins = [(plugin_name, p) for plugin_name, p in discovered if plugin_name == name]
    if not selected_plugins:
        typer.echo(f"Plugin '{name}' was not found.")
        raise typer.Exit(1)

    run_setups_for_plugins_fn(selected_plugins)
