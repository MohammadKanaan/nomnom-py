import logging
from pathlib import Path

import pytest

from nomnom.config import ConfigError, DEFAULT_PLUGIN_PRIORITY, load_config


def test_load_config_supports_plugins_key(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[[watch]]
name = "inbox"
paths = ["./inbox"]

[[plugins]]
name = "transcribe"
priority = 10
""".strip()
        + "\n"
    )

    cfg = load_config(config_path)

    assert len(cfg.watch_groups) == 1
    assert len(cfg.plugins) == 1
    assert cfg.plugins[0].name == "transcribe"
    assert cfg.plugins[0].priority == 10


@pytest.mark.xfail(reason="legacy plugin key support not yet implemented")
def test_load_config_supports_legacy_plugin_key_with_warning(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[[watch]]
name = "inbox"
paths = ["./inbox"]

[[plugin]]
name = "transcribe"
priority = 20
""".strip()
        + "\n"
    )

    caplog.set_level("WARNING")
    cfg = load_config(config_path)

    assert len(cfg.plugins) == 1
    assert cfg.plugins[0].name == "transcribe"
    assert cfg.plugins[0].priority == 20
    assert "Config key 'plugin' is deprecated" in caplog.text


def test_load_config_prefers_plugins_when_both_keys_present(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[[watch]]
name = "inbox"
paths = ["./inbox"]

[[plugins]]
name = "new-plugin"
priority = 5

[[plugin]]
name = "legacy-plugin"
priority = 90
""".strip()
        + "\n"
    )

    cfg = load_config(config_path)

    assert len(cfg.plugins) == 1
    assert cfg.plugins[0].name == "new-plugin"
    assert cfg.plugins[0].priority == 5


def test_load_config_missing_watch_key_raises(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[[plugins]]
name = "transcribe"
""".strip()
        + "\n"
    )

    with pytest.raises(ConfigError, match="missing required 'watch' key"):
        load_config(config_path)


def test_load_config_missing_name_raises(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[[watch]]
paths = ["./inbox"]
""".strip()
        + "\n"
    )

    with pytest.raises(ConfigError, match="missing required 'name' key"):
        load_config(config_path)


def test_load_config_missing_paths_raises(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[[watch]]
name = "inbox"
""".strip()
        + "\n"
    )

    with pytest.raises(ConfigError, match="missing required 'paths' key"):
        load_config(config_path)


def test_load_config_empty_plugins(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[[watch]]
name = "inbox"
paths = ["./inbox"]
""".strip()
        + "\n"
    )

    cfg = load_config(config_path)

    assert len(cfg.watch_groups) == 1
    assert cfg.plugins == []


def test_load_config_default_priority(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[[watch]]
name = "inbox"
paths = ["./inbox"]

[[plugins]]
name = "transcribe"
""".strip()
        + "\n"
    )

    cfg = load_config(config_path)

    assert len(cfg.plugins) == 1
    assert cfg.plugins[0].priority == DEFAULT_PLUGIN_PRIORITY


def test_load_config_multiple_watch_groups(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[[watch]]
name = "inbox"
paths = ["./inbox", "./shared"]

[[watch]]
name = "archive"
paths = ["./archive"]
""".strip()
        + "\n"
    )

    cfg = load_config(config_path)

    assert [group.name for group in cfg.watch_groups] == ["inbox", "archive"]
    assert cfg.watch_groups[0].paths == [tmp_path / "inbox", tmp_path / "shared"]
    assert cfg.watch_groups[1].paths == [tmp_path / "archive"]


def test_load_config_resolves_paths_relative_to_config(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[[watch]]
name = "inbox"
paths = ["./inbox"]
""".strip()
        + "\n"
    )

    cfg = load_config(config_path)

    assert cfg.watch_groups[0].paths == [tmp_path / "inbox"]


def test_load_config_absolute_paths_kept_as_is(tmp_path: Path) -> None:
    abs_path = tmp_path / "abs_inbox"
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        f"""
[[watch]]
name = "inbox"
paths = ["{abs_path}"]
""".strip()
        + "\n"
    )

    cfg = load_config(config_path)

    assert cfg.watch_groups[0].paths == [abs_path]


def test_load_config_overlap_warning(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    child_dir = tmp_path / "inbox" / "sub"
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[[watch]]
name = "parent"
paths = ["./inbox"]

[[watch]]
name = "child"
paths = ["./inbox/sub"]
""".strip()
        + "\n"
    )

    with caplog.at_level(logging.WARNING, logger="nomnom.config"):
        load_config(config_path)

    assert "Overlapping watch paths" in caplog.text
    assert "parent" in caplog.text
    assert "child" in caplog.text


def test_load_config_overlap_warning_with_dotdot_paths(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[[watch]]
name = "normalized-a"
paths = ["./a/../b"]

[[watch]]
name = "normalized-b"
paths = ["./b"]
""".strip()
        + "\n"
    )

    with caplog.at_level(logging.WARNING, logger="nomnom.config"):
        load_config(config_path)

    assert "Overlapping watch paths" in caplog.text
    assert "normalized-a" in caplog.text
    assert "normalized-b" in caplog.text


def test_default_plugin_priority_constant() -> None:
    assert DEFAULT_PLUGIN_PRIORITY == 50


def test_load_config_file_not_found(tmp_path: Path) -> None:
    missing = tmp_path / "missing.toml"

    with pytest.raises(FileNotFoundError):
        load_config(missing)


def test_load_config_watch_group_filters(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[[watch]]
name = "inbox"
paths = ["./inbox"]
include = ["*.txt", "*.md"]
exclude = ["*.tmp"]
""".strip()
        + "\n"
    )

    cfg = load_config(config_path)

    assert cfg.watch_groups[0].include == ("*.txt", "*.md")
    assert cfg.watch_groups[0].exclude == ("*.tmp",)


def test_load_config_watch_group_filters_default_empty(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[[watch]]
name = "inbox"
paths = ["./inbox"]
""".strip()
        + "\n"
    )

    cfg = load_config(config_path)

    assert cfg.watch_groups[0].include == ()
    assert cfg.watch_groups[0].exclude == ()
