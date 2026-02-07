import textwrap
from pathlib import Path

import pytest

from nomnom.config import Config, PluginConfig, WatchGroup
from nomnom.discovery import _discover_local, _load_plugin_from_target, prioritize_plugins


def test_load_plugin_from_target_rejects_absolute_module_path(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    plugin_root = tmp_path / "plugin"
    plugin_root.mkdir()

    caplog.set_level("WARNING")
    plugin = _load_plugin_from_target(plugin_root, "evil", "/tmp/malicious:EvilPlugin")

    assert plugin is None
    assert "Invalid or unsafe module path" in caplog.text


def test_discover_local_loads_valid_plugin(tmp_path: Path) -> None:
    plugins_dir = tmp_path / "plugins"
    plugin_root = plugins_dir / "nomnom-plugin-safe"
    module_dir = plugin_root / "nomnom_plugin_safe"
    module_dir.mkdir(parents=True)

    (module_dir / "__init__.py").write_text(
        textwrap.dedent(
            """
            class SafePlugin:
                def matches(self, event):
                    return False

                def handle(self, event):
                    return []
            """
        ).strip()
        + "\n"
    )

    (plugin_root / "pyproject.toml").write_text(
        textwrap.dedent(
            """
            [project]
            name = "nomnom-plugin-safe"
            version = "0.1.0"

            [project.entry-points."nomnom.plugins"]
            safe = "nomnom_plugin_safe:SafePlugin"
            """
        ).strip()
        + "\n"
    )

    discovered = _discover_local(plugins_dir)

    assert len(discovered) == 1
    name, plugin = discovered[0]
    assert name == "safe"
    assert plugin.__class__.__name__ == "SafePlugin"


def test_load_plugin_from_target_invalid_target_no_colon(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    plugin_root = tmp_path / "plugin"
    plugin_root.mkdir()

    caplog.set_level("WARNING")
    plugin = _load_plugin_from_target(plugin_root, "broken", "nomnom_plugin_broken")

    assert plugin is None
    assert "Invalid target for local plugin" in caplog.text


def test_discover_local_skips_dirs_without_pyproject(tmp_path: Path) -> None:
    plugins_dir = tmp_path / "plugins"
    (plugins_dir / "nomnom-plugin-no-meta").mkdir(parents=True)

    discovered = _discover_local(plugins_dir)

    assert discovered == []


def test_discover_local_handles_malformed_pyproject(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    plugins_dir = tmp_path / "plugins"
    broken_root = plugins_dir / "nomnom-plugin-broken"
    broken_root.mkdir(parents=True)
    (broken_root / "pyproject.toml").write_text("not: valid: toml")

    caplog.set_level("WARNING")
    discovered = _discover_local(plugins_dir)

    assert discovered == []
    assert "Failed to read local plugin" in caplog.text


def test_discover_local_empty_dir(tmp_path: Path) -> None:
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()

    discovered = _discover_local(plugins_dir)

    assert discovered == []


def test_discover_local_nonexistent_dir(tmp_path: Path) -> None:
    plugins_dir = tmp_path / "missing-plugins"

    discovered = _discover_local(plugins_dir)

    assert discovered == []


def test_prioritize_plugins_sorts_by_priority() -> None:
    plugins = [("alpha", object()), ("beta", object()), ("gamma", object())]
    config = Config(
        watch_groups=[WatchGroup(name="inbox", paths=[Path("./inbox")])],
        plugins=[
            PluginConfig(name="gamma", priority=5),
            PluginConfig(name="alpha", priority=20),
            PluginConfig(name="beta", priority=10),
        ],
    )

    prioritized = prioritize_plugins(plugins, config)

    assert [name for name, _ in prioritized] == ["gamma", "beta", "alpha"]


def test_prioritize_plugins_default_priority() -> None:
    plugins = [("configured", object()), ("defaulted", object())]
    config = Config(
        watch_groups=[WatchGroup(name="inbox", paths=[Path("./inbox")])],
        plugins=[PluginConfig(name="configured", priority=5)],
    )

    prioritized = prioritize_plugins(plugins, config)

    assert [name for name, _ in prioritized] == ["configured", "defaulted"]
