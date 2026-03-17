from dataclasses import dataclass, field
from pathlib import Path
import tomllib


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
    priority: int = 50


@dataclass
class Config:
    watch_groups: list[WatchGroup]
    plugins: list[PluginConfig] = field(default_factory=list)


def load_config(path: Path) -> Config:
    with open(path, "rb") as f:
        data = tomllib.load(f)

    watch_groups = [
        WatchGroup(
            name=w["name"],
            paths=[Path(p) for p in w["paths"]],
            include=tuple(w.get("include", [])),
            exclude=tuple(w.get("exclude", [])),
        )
        for w in data["watch"]
    ]
    plugins = [
        PluginConfig(
            name=p["name"],
            priority=p.get("priority", 50),
        )
        for p in data.get("plugins", [])
    ]
    return Config(watch_groups=watch_groups, plugins=plugins)
