import logging
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm

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
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(name)s — %(levelname)s — %(message)s",
    )
    # Suppress watchfiles debug messages unless verbose
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

    cfg = load_config(config)

    raw_plugins = discover_plugins()
    plugins = prioritize_plugins(raw_plugins, cfg)

    # Banner
    banner = Panel(
        "[bold cyan]nomnom[/] v0.1.0\n"
        f"[dim]Config: {config}[/]"
        + ("\n[bold yellow][DRY RUN][/bold yellow]" if dry_run else ""),
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
        console.print("\n[dim]One-shot mode: scanning existing files...[/]\n")
    elif dry_run:
        console.print("\n[dim]Dry-run mode: showing effects without executing...[/]\n")
    else:
        console.print("\n[dim]Watching for changes... (Ctrl+C to stop)[/]\n")

    run_watcher(cfg, plugins, console, dry_run=dry_run, once=once)


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
    import tomli_w

    console.print(
        Panel(
            "[bold cyan]nomnom Setup Wizard[/]\n"
            "[dim]Configure your file watcher interactively[/]",
            border_style="cyan",
        )
    )

    # Check if config exists
    if config.exists():
        console.print(f"\n[yellow]Found existing config at {config}[/]")
        if not Confirm.ask("Do you want to edit it?", default=True):
            console.print("[dim]Setup cancelled.[/]")
            return

        # Load existing config
        try:
            cfg = load_config(config)
            existing_watch_groups = [
                {"name": wg.name, "paths": [str(p) for p in wg.paths]}
                for wg in cfg.watch_groups
            ]
            existing_plugins = [
                {"name": p.name, "priority": p.priority}
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

    # Configure watch groups
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

    # Discover available plugins
    console.print("\n[bold]Plugins Configuration[/]")
    discovered = discover_plugins()

    if discovered:
        console.print(f"\n[dim]Discovered {len(discovered)} plugin(s):[/]")
        for plugin_name, _ in discovered:
            console.print(f"  • [magenta]{plugin_name}[/]")

    plugins = []

    if existing_plugins:
        console.print("\n[dim]Existing plugin configurations:[/]")
        for i, p in enumerate(existing_plugins, 1):
            console.print(f"  {i}. [magenta]{p['name']}[/] (priority: {p['priority']})")

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
            priority = int(Prompt.ask("Priority (lower = higher priority)", default="50"))

            plugins.append({"name": name, "priority": priority})

            if not Confirm.ask("Configure another plugin?", default=False):
                break

    # Build final config
    config_data = {
        "watch": watch_groups,
        "plugins": plugins,
    }

    # Write config
    try:
        with open(config, "wb") as f:
            tomli_w.dump(config_data, f)
        console.print(f"\n[bold green]✓[/] Configuration saved to {config}")

        # Display summary
        summary = Table(title="Configuration Summary")
        summary.add_column("Section", style="cyan")
        summary.add_column("Details", style="dim")
        summary.add_row("Watch Groups", str(len(watch_groups)))
        summary.add_row("Plugins", str(len(plugins)))
        console.print(summary)

    except Exception as e:
        console.print(f"[red]Error saving config: {e}[/]")

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
    import subprocess
    import sys

    typer.echo(f"Installing {package}...")
    installed_before = get_installed_plugin_names()
    install_cmd = ["uv", "pip", "install", "--python", sys.executable, package]

    try:
        result = subprocess.run(
            install_cmd,
            capture_output=True,
            text=True,
        )
    except OSError as e:
        typer.echo(f"Installation failed: could not execute '{install_cmd[0]}': {e}")
        raise typer.Exit(1)

    if result.returncode != 0:
        typer.echo("Installation failed:")
        error_output = result.stderr or result.stdout
        if error_output:
            typer.echo(error_output.rstrip())
        raise typer.Exit(1)

    typer.echo("Plugin installed successfully")

    if no_setup:
        typer.echo("Skipping plugin setup (--no-setup)")
        typer.echo("Run 'nomnom watch' to use it")
        return

    new_plugins = discover_new_plugins(installed_before)
    if not new_plugins:
        typer.echo("No new plugins detected after install; skipping setup.")
        typer.echo("Run 'nomnom watch' to use it")
        return

    setup_ran = False
    setup_failed = False
    for plugin_name, plugin in new_plugins:
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
            raise typer.Exit(1)
        except Exception as e:
            typer.echo(f"Setup failed for plugin '{plugin_name}': {e}")
            setup_failed = True

    if not setup_ran:
        typer.echo("No plugin setup was executed.")

    if setup_failed:
        typer.echo("One or more plugin setup steps failed.")
        raise typer.Exit(1)

    typer.echo("Run 'nomnom watch' to use it")


if __name__ == "__main__":
    app()
