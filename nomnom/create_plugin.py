import typer
import tomli_w
from rich.console import Console
from rich.panel import Panel

from nomnom.discovery import PLUGINS_DIR
from nomnom.validation import validate_plugin_name

console = Console()


def create_plugin(
    name: str = typer.Argument(help="Plugin name (e.g. 'transcribe' or 'pdf-parser')"),
) -> None:
    """Scaffold a new local plugin in the plugins/ directory."""

    # Normalize naming: hyphens for package dir, underscores for module
    try:
        slug = validate_plugin_name(name)
    except ValueError as e:
        console.print(f"[red]Invalid plugin name:[/] {e}")
        console.print(
            "[yellow]Plugin names should use letters, numbers, and hyphens[/]\n"
            "[dim]Examples: 'transcribe', 'pdf-parser', 'image-resizer'[/]"
        )
        raise typer.Exit(1)
    package_name = f"nomnom-plugin-{slug}"
    module_name = f"nomnom_plugin_{slug.replace('-', '_')}"
    class_name = "".join(word.capitalize() for word in slug.split("-")) + "Plugin"

    plugin_dir = PLUGINS_DIR / package_name
    module_dir = plugin_dir / module_name

    if plugin_dir.exists():
        console.print(f"[red]Plugin already exists at {plugin_dir}[/]")
        raise typer.Exit(1)

    # Create directories
    module_dir.mkdir(parents=True)

    # Write pyproject.toml
    pyproject_data = {
        "project": {
            "name": package_name,
            "version": "0.1.0",
            "description": f"nomnom plugin: {name}",
            "requires-python": ">=3.11",
            "dependencies": [],
            "entry-points": {
                "nomnom.plugins": {
                    slug: f"{module_name}:{class_name}",
                },
            },
        },
        "build-system": {
            "requires": ["hatchling"],
            "build-backend": "hatchling.build",
        },
    }

    with open(plugin_dir / "pyproject.toml", "wb") as f:
        tomli_w.dump(pyproject_data, f)

    # Write __init__.py with stub class
    init_content = f'''from nomnom.effects import Effect
from nomnom.events import FileEvent


class {class_name}:
    """TODO: Describe what this plugin does."""

    def matches(self, event: FileEvent) -> bool:
        # TODO: Return True for events this plugin should handle.
        # Examples:
        #   event.path.suffix == ".pdf"
        #   event.event_type == EventType.CREATED
        return False

    def handle(self, event: FileEvent) -> list[Effect]:
        # TODO: Process the event and return effects.
        # Available effects: MoveFile, DeleteFile, CreateFile, EditFile, EmitEvent
        return []
'''

    (module_dir / "__init__.py").write_text(init_content)

    # Output
    console.print(
        Panel(
            f"[bold green]Created plugin:[/] {package_name}\n\n"
            f"  [dim]{plugin_dir / 'pyproject.toml'}[/]\n"
            f"  [dim]{module_dir / '__init__.py'}[/]\n\n"
            f"Edit [magenta]{class_name}[/] in [cyan]{module_dir / '__init__.py'}[/]\n"
            f"to define your matches() and handle() logic.\n\n"
            f"Add to your config.toml:\n"
            f'  [dim][[plugins]]\n  name = "{slug}"\n  priority = 50[/]',
            title="nomnom create-plugin",
            border_style="green",
        )
    )
