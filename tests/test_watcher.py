from pathlib import Path

from watchfiles import Change

from nomnom.config import Config, WatchGroup
from nomnom.events import EventType
from nomnom.watcher import CHANGE_MAP, _build_group_index, _resolve_group


def test_build_group_index_creates_entries(tmp_path: Path) -> None:
    first = tmp_path / "inbox"
    second = tmp_path / "shared"
    config = Config(
        watch_groups=[
            WatchGroup(name="inbox", paths=[first, second]),
            WatchGroup(name="archive", paths=[tmp_path / "archive"]),
        ]
    )

    index = _build_group_index(config)
    pairs = {(path, name) for path, name in index}

    assert (first.resolve(), "inbox") in pairs
    assert (second.resolve(), "inbox") in pairs
    assert ((tmp_path / "archive").resolve(), "archive") in pairs


def test_build_group_index_sorts_longest_first(tmp_path: Path) -> None:
    shallow = tmp_path / "root"
    deep = tmp_path / "root" / "nested"
    config = Config(
        watch_groups=[
            WatchGroup(name="shallow", paths=[shallow]),
            WatchGroup(name="deep", paths=[deep]),
        ]
    )

    index = _build_group_index(config)

    assert index[0] == (deep.resolve(), "deep")
    assert index[1] == (shallow.resolve(), "shallow")


def test_resolve_group_matches_nested_path(tmp_path: Path) -> None:
    root = tmp_path / "inbox"
    deep = root / "nested"
    index = [
        (deep.resolve(), "deep"),
        (root.resolve(), "inbox"),
    ]
    file_path = deep / "file.txt"

    group = _resolve_group(file_path, index)

    assert group == "deep"


def test_resolve_group_returns_none_for_unmatched(tmp_path: Path) -> None:
    index = [((tmp_path / "inbox").resolve(), "inbox")]
    file_path = tmp_path / "outside" / "file.txt"

    group = _resolve_group(file_path, index)

    assert group is None


def test_change_map_covers_all_types() -> None:
    assert CHANGE_MAP[Change.added] is EventType.CREATED
    assert CHANGE_MAP[Change.modified] is EventType.MODIFIED
    assert CHANGE_MAP[Change.deleted] is EventType.DELETED
