import importlib.util
import logging
import sys
import tomllib
from importlib.metadata import entry_points
from pathlib import Path

from nomnom.config import Config
from nomnom.plugin import Plugin
from nomnom.validation import validate_module_path_containment

logger = logging.getLogger(__name__)

PLUGINS_DIR = Path("plugins")
ENTRY_POINT_GROUP = "nomnom.plugins"


def discover_plugins() -> list[tuple[str, Plugin]]:
    installed = _discover_installed()
    local = _discover_local()

    # local plugins override installed ones with the same name
    merged: dict[str, Plugin] = {}
    for name, plugin in installed:
        merged[name] = plugin
    for name, plugin in local:
        if name in merged:
            logger.info(f"Local plugin '{name}' overrides installed version")
        merged[name] = plugin

    return list(merged.items())


def _discover_installed() -> list[tuple[str, Plugin]]:
    plugins: list[tuple[str, Plugin]] = []
    for ep in entry_points(group=ENTRY_POINT_GROUP):
        try:
            plugin_class = ep.load()
            plugin = plugin_class()
            plugins.append((ep.name, plugin))
            logger.info(f"Loaded installed plugin: {ep.name}")
        except Exception as e:
            logger.warning(f"Failed to load installed plugin '{ep.name}': {e}")
    return plugins


def _discover_local(plugins_dir: Path = PLUGINS_DIR) -> list[tuple[str, Plugin]]:
    if not plugins_dir.is_dir():
        return []

    plugins: list[tuple[str, Plugin]] = []

    for child in sorted(plugins_dir.iterdir()):
        pyproject = child / "pyproject.toml"
        if not pyproject.is_file():
            continue

        try:
            with open(pyproject, "rb") as f:
                data = tomllib.load(f)

            ep_map = (
                data.get("project", {})
                .get("entry-points", {})
                .get(ENTRY_POINT_GROUP, {})
            )

            if not ep_map:
                continue

            for name, target in ep_map.items():
                plugin = _load_plugin_from_target(child, name, target)
                if plugin is not None:
                    plugins.append((name, plugin))

        except Exception as e:
            logger.warning(f"Failed to read local plugin at '{child}': {e}")

    return plugins


def _load_plugin_from_target(
    plugin_root: Path, name: str, target: str
) -> Plugin | None:
    """Load a plugin class from a 'module.path:ClassName' target string."""
    try:
        module_path, class_name = target.rsplit(":", 1)
    except ValueError:
        logger.warning(f"Invalid target for local plugin '{name}': {target}")
        return None

    file_path = validate_module_path_containment(plugin_root, module_path)
    if file_path is None:
        logger.warning(
            f"Invalid or unsafe module path for local plugin '{name}': "
            f"{module_path} (must be contained within plugin directory)"
        )
        return None

    try:
        spec = importlib.util.spec_from_file_location(module_path, file_path)
        if spec is None or spec.loader is None:
            logger.warning(f"Cannot create module spec for local plugin '{name}'")
            return None

        module = importlib.util.module_from_spec(spec)
        previous_module = sys.modules.get(module_path)
        sys.modules[module_path] = module
        try:
            spec.loader.exec_module(module)
        except Exception:
            if previous_module is not None:
                sys.modules[module_path] = previous_module
            else:
                sys.modules.pop(module_path, None)
            raise

        plugin_class = getattr(module, class_name)
        plugin = plugin_class()
        logger.info(f"Loaded local plugin: {name}")
        return plugin

    except Exception as e:
        logger.warning(f"Failed to load local plugin '{name}': {e}")
        return None


def prioritize_plugins(
    plugins: list[tuple[str, Plugin]],
    config: Config,
) -> list[tuple[str, Plugin]]:
    priority_map = {p.name: p.priority for p in config.plugins}
    return sorted(plugins, key=lambda p: priority_map.get(p[0], 50))
