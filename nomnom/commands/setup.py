from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from nomnom.config import DEFAULT_PLUGIN_PRIORITY, load_config
from nomnom.discovery import discover_plugins


def setup_command(
    *,
    config: Path,
    console: Console,
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
            cfg = load_config(config)
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
    discovered = discover_plugins(rules_path=config.parent.resolve() / "rules.toml")

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
            while True:
                raw = Prompt.ask(
                    "Priority (lower = higher priority)", default=str(DEFAULT_PLUGIN_PRIORITY)
                )
                try:
                    priority = int(raw)
                    break
                except ValueError:
                    console.print(f"[red]{raw!r} is not a valid integer.[/]")
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
