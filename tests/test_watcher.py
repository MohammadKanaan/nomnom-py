from pathlib import Path
from types import SimpleNamespace

import pytest
from watchfiles import Change

from nomnom.config import Config, WatchGroup
from nomnom.events import EventType
from nomnom.stats import WatchStats
from nomnom.watcher import (
    CHANGE_MAP,
    _build_group_index,
    _coalesce_changes,
    _matches_filters,
    _resolve_group,
    _scan_existing_files,
    run_watcher,
)


def test_build_group_index_creates_entries(tmp_path: Path) -> None:
    first = tmp_path / "inbox"
    second = tmp_path / "shared"
    config = Config(
        watch_groups=[
            WatchGroup(name="inbox", paths=(first, second)),
            WatchGroup(name="archive", paths=(tmp_path / "archive",)),
        ]
    )

    index = _build_group_index(config)
    pairs = {(path, group.name) for path, group in index}

    assert (first.resolve(), "inbox") in pairs
    assert (second.resolve(), "inbox") in pairs
    assert ((tmp_path / "archive").resolve(), "archive") in pairs


def test_build_group_index_sorts_longest_first(tmp_path: Path) -> None:
    shallow = tmp_path / "root"
    deep = tmp_path / "root" / "nested"
    config = Config(
        watch_groups=[
            WatchGroup(name="shallow", paths=(shallow,)),
            WatchGroup(name="deep", paths=(deep,)),
        ]
    )

    index = _build_group_index(config)

    assert index[0] == (deep.resolve(), config.watch_groups[1])
    assert index[1] == (shallow.resolve(), config.watch_groups[0])


def test_resolve_group_matches_nested_path(tmp_path: Path) -> None:
    root = tmp_path / "inbox"
    deep = root / "nested"
    index = [
        (deep.resolve(), WatchGroup(name="deep", paths=(deep,))),
        (root.resolve(), WatchGroup(name="inbox", paths=(root,))),
    ]
    file_path = deep / "file.txt"

    group = _resolve_group(file_path, index)

    assert group is not None
    assert group.name == "deep"


def test_resolve_group_returns_none_for_unmatched(tmp_path: Path) -> None:
    root = tmp_path / "inbox"
    index = [((root).resolve(), WatchGroup(name="inbox", paths=(root,)))]
    file_path = tmp_path / "outside" / "file.txt"

    group = _resolve_group(file_path, index)

    assert group is None


def test_change_map_covers_all_types() -> None:
    assert CHANGE_MAP[Change.added] is EventType.CREATED
    assert CHANGE_MAP[Change.modified] is EventType.MODIFIED
    assert CHANGE_MAP[Change.deleted] is EventType.DELETED


def test_coalesce_prefers_deleted_when_added_and_deleted_for_missing_path(
    tmp_path: Path,
) -> None:
    path = tmp_path / "churn.txt"

    result = _coalesce_changes({(Change.added, str(path)), (Change.deleted, str(path))})

    assert result == [(Change.deleted, str(path))]


def test_coalesce_prefers_added_when_added_and_deleted_for_existing_path(
    tmp_path: Path,
) -> None:
    path = tmp_path / "churn.txt"
    path.write_text("ok")

    result = _coalesce_changes({(Change.added, str(path)), (Change.deleted, str(path))})

    assert result == [(Change.added, str(path))]


def test_coalesce_prefers_added_over_modified_for_same_path(tmp_path: Path) -> None:
    path = tmp_path / "update.txt"

    result = _coalesce_changes(
        {(Change.added, str(path)), (Change.modified, str(path))}
    )

    assert result == [(Change.added, str(path))]


def test_matches_filters_include_allows_and_blocks() -> None:
    cfg = Config(
        watch_groups=[
            WatchGroup(name="inbox", paths=(Path("."),), include=("*.txt",)),
        ]
    )

    group = cfg.watch_groups[0]

    assert _matches_filters(Path("note.txt"), group) is True
    assert _matches_filters(Path("note.md"), group) is False


def test_matches_filters_exclude_blocks() -> None:
    cfg = Config(
        watch_groups=[
            WatchGroup(name="inbox", paths=(Path("."),), exclude=("*.tmp",)),
        ]
    )

    group = cfg.watch_groups[0]

    assert _matches_filters(Path("note.txt"), group) is True
    assert _matches_filters(Path("note.tmp"), group) is False


def test_matches_filters_combined() -> None:
    cfg = Config(
        watch_groups=[
            WatchGroup(
                name="inbox",
                paths=(Path("."),),
                include=("*.txt", "*.md"),
                exclude=("secret.*",),
            ),
        ]
    )

    group = cfg.watch_groups[0]

    assert _matches_filters(Path("file.txt"), group) is True
    assert _matches_filters(Path("secret.txt"), group) is False
    assert _matches_filters(Path("image.png"), group) is False


def test_matches_filters_no_patterns_allows_all() -> None:
    cfg = Config(
        watch_groups=[
            WatchGroup(name="inbox", paths=(Path("."),)),
        ]
    )

    group = cfg.watch_groups[0]

    assert _matches_filters(Path("anything.any"), group) is True


def test_scan_existing_files_creates_events(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    watch_path = tmp_path / "watch"
    watch_path.mkdir()
    (watch_path / "a.txt").write_text("a")
    (watch_path / "b.md").write_text("b")

    cfg = Config(watch_groups=[WatchGroup(name="inbox", paths=(watch_path,))])
    group_index = _build_group_index(cfg)
    dispatched: list[object] = []

    def fake_dispatch(event, plugins, **kwargs) -> None:
        dispatched.append(event)

    monkeypatch.setattr("nomnom.watcher.dispatch", fake_dispatch)

    _scan_existing_files(
        watch_paths=[watch_path.resolve()],
        group_index=group_index,
        plugins=[],
        console=SimpleNamespace(print=lambda *_args, **_kwargs: None),
        dry_run=False,
        stats=WatchStats(),
    )

    assert len(dispatched) == 2
    assert {event.event_type for event in dispatched} == {EventType.CREATED}
    assert {type(event.watch_group) for event in dispatched} == {str}


def test_scan_existing_files_respects_filters(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    watch_path = tmp_path / "watch"
    watch_path.mkdir()
    (watch_path / "a.txt").write_text("a")
    (watch_path / "b.tmp").write_text("b")
    (watch_path / "c.md").write_text("c")

    cfg = Config(
        watch_groups=[
            WatchGroup(
                name="inbox",
                paths=(watch_path,),
                include=("*.txt", "*.tmp"),
                exclude=("*.tmp",),
            )
        ]
    )
    group_index = _build_group_index(cfg)
    dispatched: list[object] = []

    def fake_dispatch(event, plugins, **kwargs) -> None:
        dispatched.append(event)

    monkeypatch.setattr("nomnom.watcher.dispatch", fake_dispatch)

    _scan_existing_files(
        watch_paths=[watch_path.resolve()],
        group_index=group_index,
        plugins=[],
        console=SimpleNamespace(print=lambda *_args, **_kwargs: None),
        dry_run=True,
        stats=WatchStats(),
    )

    assert [event.path.name for event in dispatched] == ["a.txt"]


def test_run_watcher_prints_summary_on_keyboard_interrupt(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    watch_path = tmp_path / "inbox"
    watch_path.mkdir()

    cfg = Config(
        watch_groups=[WatchGroup(name="inbox", paths=(watch_path,))], plugins=[]
    )

    class StubConsole:
        def __init__(self) -> None:
            self.calls: list[object] = []

        def print(self, value) -> None:
            self.calls.append(value)

    def interrupted_watch(*_args):
        raise KeyboardInterrupt
        yield  # pragma: no cover

    console = StubConsole()

    monkeypatch.setattr("nomnom.watcher.watch", interrupted_watch)

    run_watcher(cfg, [], console)

    assert any(
        getattr(call, "title", None) == "Watch Summary" for call in console.calls
    )


def test_run_watcher_once_scans_only_selected_group(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    inbox = tmp_path / "inbox"
    archive = tmp_path / "archive"
    inbox.mkdir()
    archive.mkdir()
    (inbox / "a.txt").write_text("a")
    (archive / "b.txt").write_text("b")

    cfg = Config(
        watch_groups=[
            WatchGroup(name="inbox", paths=(inbox,)),
            WatchGroup(name="archive", paths=(archive,)),
        ],
        plugins=[],
    )

    class StubConsole:
        def print(self, _value) -> None:
            return

    emitted: list[object] = []

    def fake_dispatch(event, _plugins, **_kwargs):
        emitted.append(event)

    monkeypatch.setattr("nomnom.watcher.dispatch", fake_dispatch)

    run_watcher(cfg, [], StubConsole(), once=True, once_watch_group="archive")

    assert [event.path.name for event in emitted] == ["b.txt"]
    assert [event.watch_group for event in emitted] == ["archive"]


def test_run_watcher_filters_use_matched_root_when_group_names_repeat(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    first_root = tmp_path / "a"
    second_root = tmp_path / "b"
    first_root.mkdir()
    second_root.mkdir()

    cfg = Config(
        watch_groups=[
            WatchGroup(name="inbox", paths=(first_root,), include=("*.txt",)),
            WatchGroup(name="inbox", paths=(second_root,), include=("*.md",)),
        ],
        plugins=[],
    )

    class StubConsole:
        def print(self, _value) -> None:
            return

    emitted: list[object] = []

    def fake_watch(*_args):
        yield {(Change.added, str(second_root / "note.md"))}

    def fake_dispatch(event, _plugins, **_kwargs):
        emitted.append(event)

    monkeypatch.setattr("nomnom.watcher.watch", fake_watch)
    monkeypatch.setattr("nomnom.watcher.dispatch", fake_dispatch)

    run_watcher(cfg, [], StubConsole())

    assert len(emitted) == 1
