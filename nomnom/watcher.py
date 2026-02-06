import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from watchfiles import Change, watch

from nomnom.config import Config
from nomnom.dispatcher import dispatch
from nomnom.events import EventType, FileEvent
from nomnom.plugin import Plugin

if TYPE_CHECKING:
    from rich.console import Console

logger = logging.getLogger(__name__)

CHANGE_MAP = {
    Change.added: EventType.CREATED,
    Change.modified: EventType.MODIFIED,
    Change.deleted: EventType.DELETED,
}

EVENT_STYLES = {
    EventType.CREATED: ("green", "+"),
    EventType.MODIFIED: ("yellow", "~"),
    EventType.DELETED: ("red", "-"),
}


def _build_group_index(config: Config) -> list[tuple[Path, str]]:
    index: list[tuple[Path, str]] = []
    for group in config.watch_groups:
        for path in group.paths:
            index.append((path.resolve(), group.name))
    return sorted(index, key=lambda entry: len(entry[0].parts), reverse=True)


def _resolve_group(path: Path, index: list[tuple[Path, str]]) -> str | None:
    resolved = path.resolve(strict=False)
    for root, group_name in index:
        try:
            resolved.relative_to(root)
            return group_name
        except ValueError:
            continue
    return None


def run_watcher(cfg: Config, plugins: list[tuple[str, Plugin]], console: "Console") -> None:
    all_paths = [path.resolve() for group in cfg.watch_groups for path in group.paths]

    # Filter out non-existent paths
    watch_paths = []
    for path in all_paths:
        if not path.exists():
            logger.warning(f"Path does not exist, skipping: {path}")
        else:
            watch_paths.append(path)

    if not watch_paths:
        logger.error("No valid paths to watch")
        return

    group_index = _build_group_index(cfg)

    try:
        for changes in watch(*watch_paths):
            for change_type, changed in changes:
                event_type = CHANGE_MAP.get(change_type)
                if event_type is None:
                    continue

                path = Path(changed)
                watch_group = _resolve_group(path, group_index)
                if watch_group is None:
                    continue

                event = FileEvent(
                    event_type=event_type,
                    path=path,
                    watch_group=watch_group,
                    created_at=datetime.now(),
                )

                # Color-coded event display
                color, symbol = EVENT_STYLES[event_type]
                timestamp = event.created_at.strftime("%H:%M:%S")
                console.print(
                    f"[dim]{timestamp}[/] "
                    f"[{color}]{symbol}[/] "
                    f"[{color}]{event_type.value.upper()}[/]  "
                    f"{path.name}  "
                    f"[dim]{watch_group}[/]"
                )

                dispatch(event, plugins)
    except KeyboardInterrupt:
        return
