from datetime import datetime
from pathlib import Path

import pytest

from nomnom.effects import DeleteFile, EditAction, EditFile, MoveFile
from nomnom.events import EventType, FileEvent


@pytest.fixture
def rules_module(monkeypatch: pytest.MonkeyPatch):
    plugin_root = (
        Path(__file__).resolve().parent.parent / "plugins" / "nomnom-plugin-rules"
    )
    monkeypatch.syspath_prepend(str(plugin_root))
    import importlib

    return importlib.import_module("nomnom_plugin_rules")


def make_event(
    *,
    event_type: EventType = EventType.CREATED,
    path: str = "/tmp/example.txt",
    watch_group: str = "default",
) -> FileEvent:
    return FileEvent(
        event_type=event_type,
        path=Path(path),
        watch_group=watch_group,
        created_at=datetime.now(),
    )


def test_loads_rules_and_logs_notice(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    rules_module,
) -> None:
    rules_toml = tmp_path / "rules.toml"
    rules_toml.write_text(
        """
[[rule]]
name = "archive pdfs"
on = "created"
match = "\\\\.pdf$"
action = "move"
destination = "./archive/"
""".strip()
        + "\n"
    )

    monkeypatch.setattr(rules_module, "RULES_PATH", rules_toml)
    caplog.set_level("INFO")

    plugin = rules_module.RulesPlugin()

    assert len(plugin._rules) == 1
    assert "Loaded 1 rule(s)" in caplog.text
    assert "Restart nomnom to pick up changes" in caplog.text


def test_missing_rules_file_is_graceful(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    rules_module,
) -> None:
    missing = tmp_path / "rules.toml"
    monkeypatch.setattr(rules_module, "RULES_PATH", missing)
    caplog.set_level("INFO")

    plugin = rules_module.RulesPlugin()

    assert plugin._rules == []
    assert "Rules file not found" in caplog.text


def test_invalid_rules_are_skipped_with_warning(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    rules_module,
) -> None:
    rules_toml = tmp_path / "rules.toml"
    rules_toml.write_text(
        """
[[rule]]
name = "valid delete"
on = "deleted"
match = "\\\\.tmp$"
action = "delete"

[[rule]]
name = "bad event"
on = "renamed"
match = "."
action = "delete"

[[rule]]
name = "bad action"
on = "created"
match = "."
action = "compress"

[[rule]]
name = "missing move destination"
on = "created"
match = "."
action = "move"
""".strip()
        + "\n"
    )

    monkeypatch.setattr(rules_module, "RULES_PATH", rules_toml)
    caplog.set_level("WARNING")

    plugin = rules_module.RulesPlugin()

    assert len(plugin._rules) == 1
    assert "Skipping invalid rule" in caplog.text


def test_matches_on_event_filename_and_optional_watch_group(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    rules_module,
) -> None:
    rules_toml = tmp_path / "rules.toml"
    rules_toml.write_text(
        """
[[rule]]
name = "inbox markdown"
on = "created"
match = "\\\\.md$"
watch_group = "inbox"
action = "prepend"
content = "DRAFT\\n"
""".strip()
        + "\n"
    )

    monkeypatch.setattr(rules_module, "RULES_PATH", rules_toml)
    plugin = rules_module.RulesPlugin()

    assert plugin.matches(make_event(path="/tmp/note.md", watch_group="inbox"))
    assert not plugin.matches(make_event(path="/tmp/note.md", watch_group="other"))
    assert not plugin.matches(
        make_event(
            path="/tmp/note.md", watch_group="inbox", event_type=EventType.MODIFIED
        )
    )
    assert not plugin.matches(make_event(path="/tmp/note.txt", watch_group="inbox"))


def test_rule_without_watch_group_applies_to_all_groups(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    rules_module,
) -> None:
    rules_toml = tmp_path / "rules.toml"
    rules_toml.write_text(
        """
[[rule]]
name = "all markdown"
on = "created"
match = "\\\\.md$"
action = "append"
content = "\\n# tagged"
""".strip()
        + "\n"
    )
    monkeypatch.setattr(rules_module, "RULES_PATH", rules_toml)

    plugin = rules_module.RulesPlugin()

    assert plugin.matches(make_event(path="/tmp/a.md", watch_group="one"))
    assert plugin.matches(make_event(path="/tmp/b.md", watch_group="two"))


def test_all_actions_build_expected_effects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    rules_module,
) -> None:
    rules_toml = tmp_path / "rules.toml"
    rules_toml.write_text(
        """
[[rule]]
name = "prepend text"
on = "created"
match = "^prepend\\\\.txt$"
action = "prepend"
content = "HEAD"

[[rule]]
name = "append text"
on = "created"
match = "^append\\\\.txt$"
action = "append"
content = "TAIL"

[[rule]]
name = "delete temp"
on = "created"
match = "^delete\\\\.txt$"
action = "delete"

[[rule]]
name = "move file"
on = "created"
match = "^move\\\\.txt$"
action = "move"
destination = "./archive/"
""".strip()
        + "\n"
    )
    monkeypatch.setattr(rules_module, "RULES_PATH", rules_toml)
    plugin = rules_module.RulesPlugin()

    prepend_effects = plugin.handle(make_event(path="/tmp/prepend.txt"))
    append_effects = plugin.handle(make_event(path="/tmp/append.txt"))
    delete_effects = plugin.handle(make_event(path="/tmp/delete.txt"))
    move_effects = plugin.handle(make_event(path="/tmp/move.txt"))

    assert prepend_effects == [
        EditFile(
            path=Path("/tmp/prepend.txt"), action=EditAction.PREPEND, content=b"HEAD"
        )
    ]
    assert append_effects == [
        EditFile(
            path=Path("/tmp/append.txt"), action=EditAction.APPEND, content=b"TAIL"
        )
    ]
    assert delete_effects == [DeleteFile(path=Path("/tmp/delete.txt"))]
    assert move_effects == [
        MoveFile(source=Path("/tmp/move.txt"), destination=Path("archive") / "move.txt")
    ]


def test_move_to_explicit_file_path_uses_path_as_is(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    rules_module,
) -> None:
    rules_toml = tmp_path / "rules.toml"
    rules_toml.write_text(
        """
[[rule]]
name = "rename report"
on = "created"
match = "\\\\.txt$"
action = "move"
destination = "./archive/renamed.txt"
""".strip()
        + "\n"
    )
    monkeypatch.setattr(rules_module, "RULES_PATH", rules_toml)

    plugin = rules_module.RulesPlugin()
    effects = plugin.handle(make_event(path="/tmp/input.txt"))

    assert effects == [
        MoveFile(source=Path("/tmp/input.txt"), destination=Path("archive/renamed.txt"))
    ]


def test_move_to_existing_directory_preserves_filename(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    rules_module,
) -> None:
    destination_dir = tmp_path / "archive"
    destination_dir.mkdir()
    rules_toml = tmp_path / "rules.toml"
    rules_toml.write_text(
        f"""
[[rule]]
name = "archive anything"
on = "created"
match = "."
action = "move"
destination = "{destination_dir}"
""".strip()
        + "\n"
    )
    monkeypatch.setattr(rules_module, "RULES_PATH", rules_toml)

    plugin = rules_module.RulesPlugin()
    effects = plugin.handle(make_event(path="/tmp/file.dat"))

    assert effects == [
        MoveFile(source=Path("/tmp/file.dat"), destination=destination_dir / "file.dat")
    ]


def test_multiple_matching_rules_run_in_file_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    rules_module,
) -> None:
    rules_toml = tmp_path / "rules.toml"
    rules_toml.write_text(
        """
[[rule]]
name = "prepend header"
on = "created"
match = "\\\\.txt$"
action = "prepend"
content = "A"

[[rule]]
name = "append footer"
on = "created"
match = "\\\\.txt$"
action = "append"
content = "B"
""".strip()
        + "\n"
    )
    monkeypatch.setattr(rules_module, "RULES_PATH", rules_toml)

    plugin = rules_module.RulesPlugin()
    effects = plugin.handle(make_event(path="/tmp/file.txt"))

    assert effects == [
        EditFile(path=Path("/tmp/file.txt"), action=EditAction.PREPEND, content=b"A"),
        EditFile(path=Path("/tmp/file.txt"), action=EditAction.APPEND, content=b"B"),
    ]
