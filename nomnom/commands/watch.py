import logging
from pathlib import Path

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.table import Table

import nomnom
from nomnom.config import load_config
from nomnom.discovery import discover_plugins, prioritize_plugins
from nomnom.watcher import run_watcher

NOMNOM_ASCII = """\
,--,--,  ,---. ,--,--,--.,--,--,  ,---. ,--,--,--.
|      \\| .-. ||        ||      \\| .-. ||        |
|  ||  |' '-' '|  |  |  ||  ||  |' '-' '|  |  |  |
`--''--' `---' `--`--`--'`--''--' `---' `--`--`--'
"""


def show_ascii_splash(console: Console) -> None:
    """Display ASCII art splash screen."""
    console.print(Panel(f"[#F9B2D7]{NOMNOM_ASCII}[/#F9B2D7]", border_style="cyan", padding=(1, 2)))
    console.print()


def watch_command(
    *,
    once_watch_group: str | None,
    config: Path,
    verbose: bool,
    dry_run: bool,
    once: bool,
    console: Console,
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

    cfg = load_config(config)
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

    raw_plugins = discover_plugins(rules_path=config.parent.resolve() / "rules.toml")
    prioritized_plugins = prioritize_plugins(raw_plugins, cfg)

    config_plugin_status = {p.name: p.enabled for p in cfg.plugins}
    plugins = [
        entry
        for entry in prioritized_plugins
        if config_plugin_status.get(entry.name, True)
    ]

    show_ascii_splash(console)

    banner = Panel(
        f"[bold cyan]nomnom[/] v{nomnom.get_version()}\n"
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

    run_watcher(
        cfg,
        plugins,
        console,
        dry_run=dry_run,
        once=once,
        once_watch_group=once_watch_group,
    )
