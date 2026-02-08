import logging
from datetime import datetime
from fnmatch import fnmatch
from pathlib import Path
from typing import TYPE_CHECKING

from watchfiles import Change, watch

from nomnom.config import Config
from nomnom.dispatcher import dispatch
from nomnom.events import EventType, FileEvent
from nomnom.plugin import Plugin
from nomnom.stats import WatchStats

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

RawChange = tuple[Change, str]
GroupIndexEntry = tuple[Path, str]


def _watch_root_specificity(entry: GroupIndexEntry) -> int:
    """Higher value means a deeper (more specific) watch root."""
    root_path, _group_name = entry
    return len(root_path.parts)


def _build_group_index(config: Config) -> list[GroupIndexEntry]:
    index: list[GroupIndexEntry] = []
    for group in config.watch_groups:
        for path in group.paths:
            index.append((path.resolve(), group.name))
    return sorted(index, key=_watch_root_specificity, reverse=True)


def _resolve_group(path: Path, index: list[GroupIndexEntry]) -> str | None:
    resolved = path.resolve(strict=False)
    for root, group_name in index:
        try:
            resolved.relative_to(root)
            return group_name
        except ValueError:
            continue
    return None


def _change_sort_key(item: RawChange) -> tuple[str, int]:
    """Stable sort key: path first, then watchfiles change enum value."""
    change_type, changed = item
    return str(changed), int(change_type)


def _coalesce_changes(changes: set[RawChange]) -> list[RawChange]:
    """Reduce noisy watchfiles batches to one effective change per path."""
    by_path: dict[str, set[Change]] = {}
    for change_type, changed in changes:
        by_path.setdefault(changed, set()).add(change_type)

    coalesced: list[RawChange] = []
    for changed, change_types in by_path.items():
        path_exists = Path(changed).exists()

        if Change.added in change_types and Change.deleted in change_types:
            selected = Change.added if path_exists else Change.deleted
        elif Change.added in change_types:
            selected = Change.added
        elif Change.deleted in change_types:
            selected = Change.deleted
        elif Change.modified in change_types:
            selected = Change.modified
        else:
            continue

        coalesced.append((selected, changed))

    return sorted(coalesced, key=_change_sort_key)


def _matches_filters(path: Path, cfg: Config, group_name: str) -> bool:
    group = next((g for g in cfg.watch_groups if g.name == group_name), None)
    if group is None:
        return True

    if group.include and not any(fnmatch(path.name, pattern) for pattern in group.include):
        return False

    if group.exclude and any(fnmatch(path.name, pattern) for pattern in group.exclude):
        return False

    return True


def _scan_existing_files(
    watch_paths: list[Path],
    group_index: list[GroupIndexEntry],
    cfg: Config,
    plugins: list[tuple[str, Plugin]],
    console: "Console",
    dry_run: bool,
    stats: WatchStats,
) -> None:
    for watch_path in watch_paths:
        for path in sorted(p for p in watch_path.rglob("*") if p.is_file()):
            watch_group = _resolve_group(path, group_index)
            if watch_group is None:
                continue
            if not _matches_filters(path, cfg, watch_group):
                continue

            event = FileEvent(
                event_type=EventType.CREATED,
                path=path,
                watch_group=watch_group,
                created_at=datetime.now(),
            )

            color, symbol = EVENT_STYLES[EventType.CREATED]
            timestamp = event.created_at.strftime("%H:%M:%S")
            console.print(
                f"[dim]{timestamp}[/] "
                f"[{color}]{symbol}[/] "
                f"[{color}]{event.event_type.value.upper()}[/]  "
                f"{path.name}  "
                f"[dim]{watch_group}[/]"
            )

            dispatch(event, plugins, dry_run=dry_run, stats=stats)


def run_watcher(
    cfg: Config,
    plugins: list[tuple[str, Plugin]],
    console: "Console",
    *,
    dry_run: bool = False,
    once: bool = False,
) -> None:
    stats = WatchStats()
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

    if once:
        _scan_existing_files(
            watch_paths,
            group_index,
            cfg,
            plugins,
            console,
            dry_run,
            stats,
        )
        stats.print_summary(console)
        return

    try:
        for raw_changes in watch(*watch_paths):
            for change_type, changed in _coalesce_changes(raw_changes):
                event_type = CHANGE_MAP.get(change_type)
                if event_type is None:
                    continue

                path = Path(changed)
                watch_group = _resolve_group(path, group_index)
                if watch_group is None:
                    continue
                if not _matches_filters(path, cfg, watch_group):
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

                dispatch(event, plugins, dry_run=dry_run, stats=stats)
    except KeyboardInterrupt:
        stats.print_summary(console)
        return
