from pathlib import Path

import pytest

from nomnom.config import load_config


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

    with pytest.raises(KeyError):
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
    assert cfg.plugins[0].priority == 50


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
    assert cfg.watch_groups[0].paths == (Path("./inbox"), Path("./shared"))
    assert cfg.watch_groups[1].paths == (Path("./archive"),)


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
