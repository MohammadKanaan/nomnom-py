import logging
from importlib.metadata import entry_points

from nomnom.config import Config
from nomnom.plugin import Plugin

logger = logging.getLogger(__name__)


def discover_plugins() -> list[tuple[str, Plugin]]:
    plugins: list[tuple[str, Plugin]] = []
    for ep in entry_points(group="nomnom.plugins"):
        try:
            plugin_class = ep.load()
            plugin = plugin_class()
            plugins.append((ep.name, plugin))
            logger.info(f"Loaded plugin: {ep.name}")
        except Exception as e:
            logger.warning(f"Failed to load plugin '{ep.name}': {e}")
    return plugins


def prioritize_plugins(
    plugins: list[tuple[str, Plugin]],
    config: Config,
) -> list[tuple[str, Plugin]]:
    priority_map = {p.name: p.priority for p in config.plugins}
    return sorted(plugins, key=lambda p: priority_map.get(p[0], 50))
