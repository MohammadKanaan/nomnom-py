import functools
import logging
from datetime import datetime
from fnmatch import fnmatch
from pathlib import Path
from typing import TYPE_CHECKING

from rich.markup import escape
from watchfiles import Change, watch

from nomnom.config import Config, WatchGroup
from nomnom.dispatcher import dispatch
from nomnom.events import EventType, FileEvent
from nomnom.executor import EFFECT_TEMPFILE_PREFIX
from nomnom.plugin import PluginEntry
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
GroupIndexEntry = tuple[Path, WatchGroup]


def _watch_root_specificity(entry: GroupIndexEntry) -> int:
    """Higher value means a deeper (more specific) watch root."""
    root_path, _group = entry
    return len(root_path.parts)


def _build_group_index(watch_groups: list[WatchGroup]) -> list[GroupIndexEntry]:
    index: list[GroupIndexEntry] = []
    for group in watch_groups:
        for path in group.paths:
            index.append((path.resolve(), group))
    return sorted(index, key=_watch_root_specificity, reverse=True)


def _resolve_group(path: Path, index: list[GroupIndexEntry]) -> WatchGroup | None:
    resolved = path.resolve(strict=False)
    for root, group in index:
        if resolved.is_relative_to(root):
            return group
    return None


def _change_sort_key(item: RawChange) -> tuple[str, int]:
    """Stable sort key: path first, then watchfiles change enum value."""
    change_type, changed = item
    return str(changed), int(change_type)


def _is_internal_temp_path(changed: str) -> bool:
    return Path(changed).name.startswith(EFFECT_TEMPFILE_PREFIX)


def _coalesce_changes(
    changes: set[RawChange],
    known_paths: set[str] | None = None,
) -> list[RawChange]:
    """Reduce noisy watchfiles batches to one effective change per path."""
    if known_paths is None:
        known_paths = set()

    # Standard per-path coalescing
    by_path: dict[str, set[Change]] = {}
    for change_type, changed in changes:
        if _is_internal_temp_path(changed):
            continue
        by_path.setdefault(changed, set()).add(change_type)

    coalesced: list[RawChange] = []
    for changed, change_types in by_path.items():
        if Change.added in change_types and Change.deleted in change_types:
            path_exists = Path(changed).exists()
            selected = Change.added if path_exists else Change.deleted
        elif Change.added in change_types:
            selected = Change.added
        elif Change.deleted in change_types:
            selected = Change.deleted
        elif Change.modified in change_types:
            selected = Change.modified
        else:
            continue

        # Downgrade CREATED → MODIFIED if path is already known (atomic write from any source)
        if selected == Change.added and changed in known_paths:
            selected = Change.modified
        elif selected == Change.added:
            known_paths.add(changed)

        if selected == Change.deleted:
            known_paths.discard(changed)

        coalesced.append((selected, changed))

    return sorted(coalesced, key=_change_sort_key)


@functools.lru_cache(maxsize=1024)
def _matches_patterns(name: str, patterns: tuple[str, ...]) -> bool:
    """Cache fnmatch evaluations against multiple patterns to reduce overhead."""
    return any(fnmatch(name, pattern) for pattern in patterns)


def _matches_filters(path: Path, group: WatchGroup) -> bool:
    if group.include and not _matches_patterns(path.name, group.include):
        return False

    return not (group.exclude and _matches_patterns(path.name, group.exclude))


def _print_event(console: "Console", event: FileEvent) -> None:
    color, symbol = EVENT_STYLES[event.event_type]
    timestamp = event.created_at.strftime("%H:%M:%S")
    console.print(
        f"[dim]{timestamp}[/] "
        f"[{color}]{symbol}[/] "
        f"[{color}]{event.event_type.value.upper()}[/]  "
        f"{escape(event.path.name)}  "
        f"[dim]{escape(event.watch_group)}[/]"
    )


def _scan_existing_files(
    watch_paths: list[Path],
    group_index: list[GroupIndexEntry],
    plugins: list[PluginEntry],
    console: "Console",
    dry_run: bool,
    stats: WatchStats,
) -> None:
    for watch_path in watch_paths:
        for path in sorted(p for p in watch_path.rglob("*") if p.is_file()):
            watch_group = _resolve_group(path, group_index)
            if watch_group is None:
                continue
            if not _matches_filters(path, watch_group):
                continue

            event = FileEvent(
                event_type=EventType.CREATED,
                path=path,
                watch_group=watch_group.name,
                created_at=datetime.now(),
            )

            _print_event(console, event)

            dispatch(event, plugins, dry_run=dry_run, stats=stats)


def run_watcher(
    cfg: Config,
    plugins: list[PluginEntry],
    console: "Console",
    *,
    dry_run: bool = False,
    once: bool = False,
    once_watch_group: str | None = None,
) -> None:
    stats = WatchStats()
    active_watch_groups = cfg.watch_groups
    if once and once_watch_group is not None:
        active_watch_groups = [
            group for group in cfg.watch_groups if group.name == once_watch_group
        ]

    all_paths = [
        path.resolve() for group in active_watch_groups for path in group.paths
    ]

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

    group_index = _build_group_index(active_watch_groups)

    if once:
        _scan_existing_files(
            watch_paths,
            group_index,
            plugins,
            console,
            dry_run,
            stats,
        )
        stats.print_summary(console)
        return

    try:
        known_paths: set[str] = set()
        for watch_path in watch_paths:
            known_paths.update(str(p) for p in watch_path.rglob("*") if p.is_file())
        for raw_changes in watch(*watch_paths):
            for change_type, changed in _coalesce_changes(raw_changes, known_paths):
                event_type = CHANGE_MAP.get(change_type)
                if event_type is None:
                    continue

                path = Path(changed)
                watch_group = _resolve_group(path, group_index)
                if watch_group is None:
                    continue
                if not _matches_filters(path, watch_group):
                    continue

                event = FileEvent(
                    event_type=event_type,
                    path=path,
                    watch_group=watch_group.name,
                    created_at=datetime.now(),
                )

                _print_event(console, event)

                dispatch(event, plugins, dry_run=dry_run, stats=stats)
    except KeyboardInterrupt:
        pass
    except OSError as exc:
        logger.warning("Filesystem watcher encountered an unrecoverable error: %s", exc)
    finally:
        stats.print_summary(console)
