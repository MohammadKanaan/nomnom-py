from dataclasses import dataclass, field
from pathlib import Path
import tomllib


@dataclass
class WatchGroup:
    name: str
    paths: list[Path]
    include: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)


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
            include=list(w.get("include", [])),
            exclude=list(w.get("exclude", [])),
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
