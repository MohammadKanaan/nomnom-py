import logging
from dataclasses import dataclass, field
from pathlib import Path
import tomllib

logger = logging.getLogger(__name__)

DEFAULT_PLUGIN_PRIORITY = 50


class ConfigError(ValueError):
    pass


@dataclass
class WatchGroup:
    name: str
    paths: list[Path]
    include: tuple[str, ...] = field(default_factory=tuple)
    exclude: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if isinstance(self.include, list):
            self.include = tuple(self.include)
        if isinstance(self.exclude, list):
            self.exclude = tuple(self.exclude)


@dataclass
class PluginConfig:
    name: str
    priority: int = DEFAULT_PLUGIN_PRIORITY
    enabled: bool = True


@dataclass
class Config:
    watch_groups: list[WatchGroup]
    plugins: list[PluginConfig] = field(default_factory=list)


def load_config(path: Path) -> Config:
    with open(path, "rb") as f:
        data = tomllib.load(f)

    if "watch" not in data:
        raise ConfigError("Config is missing required 'watch' key")
    for i, w in enumerate(data["watch"]):
        if "name" not in w:
            raise ConfigError(f"Watch group at index {i} is missing required 'name' key")
        if "paths" not in w:
            raise ConfigError(f"Watch group '{w['name']}' is missing required 'paths' key")

    config_dir = path.parent.resolve()

    watch_groups = [
        WatchGroup(
            name=w["name"],
            paths=[
                config_dir / Path(p).expanduser() if not Path(p).expanduser().is_absolute()
                else Path(p).expanduser()
                for p in w["paths"]
            ],
            include=tuple(w.get("include", [])),
            exclude=tuple(w.get("exclude", [])),
        )
        for w in data["watch"]
    ]
    plugins = [
        PluginConfig(
            name=p["name"],
            priority=p.get("priority", DEFAULT_PLUGIN_PRIORITY),
            enabled=p.get("enabled", True),
        )
        for p in data.get("plugins", [])
    ]

    all_paths = [
        (wg.name, p, p.resolve(strict=False)) for wg in watch_groups for p in wg.paths
    ]
    for i, (name_a, path_a, normalized_a) in enumerate(all_paths):
        for name_b, path_b, normalized_b in all_paths[i + 1:]:
            if name_a == name_b:
                continue
            if normalized_a.is_relative_to(normalized_b) or normalized_b.is_relative_to(
                normalized_a
            ):
                common_path = (
                    normalized_b
                    if normalized_a.is_relative_to(normalized_b)
                    else normalized_a
                )
                logger.warning(
                    "Overlapping watch paths detected between groups '%s' and '%s'. "
                    "Common path: %s. %s path: %s. %s path: %s.",
                    name_a,
                    name_b,
                    common_path,
                    name_a,
                    path_a,
                    name_b,
                    path_b,
                )

    return Config(watch_groups=watch_groups, plugins=plugins)
