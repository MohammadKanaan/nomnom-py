import textwrap
from pathlib import Path

import pytest

import nomnom.discovery as discovery_module
from nomnom.config import Config, PluginConfig, WatchGroup
from nomnom.discovery import (
    _discover_local,
    _load_plugin_from_target,
    discover_new_plugins,
    discover_plugins,
    get_installed_plugin_names,
    prioritize_plugins,
)
from nomnom.plugin import PluginEntry


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


def test_discover_local_loads_dataclass_plugin_with_future_annotations(
    tmp_path: Path,
) -> None:
    plugins_dir = tmp_path / "plugins"
    plugin_root = plugins_dir / "nomnom-plugin-fancy"
    module_dir = plugin_root / "nomnom_plugin_fancy"
    module_dir.mkdir(parents=True)

    (module_dir / "__init__.py").write_text(
        textwrap.dedent(
            """
            from __future__ import annotations

            from dataclasses import dataclass

            @dataclass
            class Payload:
                values: list[str]

            class FancyPlugin:
                def __init__(self):
                    self.payload = Payload(values=[])

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
            name = "nomnom-plugin-fancy"
            version = "0.1.0"

            [project.entry-points."nomnom.plugins"]
            fancy = "nomnom_plugin_fancy:FancyPlugin"
            """
        ).strip()
        + "\n"
    )

    discovered = _discover_local(plugins_dir)

    assert len(discovered) == 1
    name, plugin = discovered[0]
    assert name == "fancy"
    assert plugin.__class__.__name__ == "FancyPlugin"


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
    plugins = [
        PluginEntry("alpha", object()),
        PluginEntry("beta", object()),
        PluginEntry("gamma", object()),
    ]
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
    plugins = [PluginEntry("configured", object()), PluginEntry("defaulted", object())]
    config = Config(
        watch_groups=[WatchGroup(name="inbox", paths=[Path("./inbox")])],
        plugins=[PluginConfig(name="configured", priority=5)],
    )

    prioritized = prioritize_plugins(plugins, config)

    assert [name for name, _ in prioritized] == ["configured", "defaulted"]


def test_get_installed_plugin_names(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeEntryPoint:
        def __init__(self, name: str) -> None:
            self.name = name

    monkeypatch.setattr(
        discovery_module,
        "_discover_builtin",
        lambda: (_ for _ in ()).throw(AssertionError("builtin discovery should not run")),
    )
    monkeypatch.setattr(
        discovery_module,
        "entry_points",
        lambda group: [FakeEntryPoint("alpha"), FakeEntryPoint("beta")],
    )

    assert get_installed_plugin_names() == {"alpha", "beta"}


def test_discover_plugins_returns_builtin_rules_without_installed_or_local(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(discovery_module, "_discover_installed", lambda: [])
    monkeypatch.setattr(discovery_module, "_discover_local", lambda: [])

    discovered = discover_plugins()
    discovered_map = {name: plugin for name, plugin in discovered}

    assert "rules" in discovered_map
    assert discovered_map["rules"].__class__.__name__ == "RulesPlugin"


def test_discover_plugins_uses_rules_path_for_builtin_rules(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    rules_toml = project_root / "rules.toml"
    rules_toml.write_text(
        """
[[rule]]
name = "delete markdown"
on = "created"
match = "\\\\.md$"
action = "delete"
""".strip()
        + "\n"
    )

    other_cwd = tmp_path / "other-cwd"
    other_cwd.mkdir()
    monkeypatch.chdir(other_cwd)
    monkeypatch.setattr(discovery_module, "_discover_installed", lambda: [])
    monkeypatch.setattr(discovery_module, "_discover_local", lambda: [])

    discovered = discover_plugins(rules_path=rules_toml)
    discovered_map = {name: plugin for name, plugin in discovered}

    rules_plugin = discovered_map["rules"]
    assert len(rules_plugin._rules) == 1
    assert rules_plugin._rules[0].name == "delete markdown"


def test_discover_plugins_prefers_rules_path_over_cwd(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "rules.toml").write_text(
        """
[[rule]]
name = "project rule"
on = "created"
match = "\\\\.md$"
action = "delete"
""".strip()
        + "\n"
    )

    cwd_root = tmp_path / "cwd"
    cwd_root.mkdir()
    (cwd_root / "rules.toml").write_text(
        """
[[rule]]
name = "cwd rule"
on = "created"
match = "\\\\.txt$"
action = "delete"
""".strip()
        + "\n"
    )

    monkeypatch.chdir(cwd_root)
    monkeypatch.setattr(discovery_module, "_discover_installed", lambda: [])
    monkeypatch.setattr(discovery_module, "_discover_local", lambda: [])

    discovered = discover_plugins(rules_path=project_root / "rules.toml")
    discovered_map = {name: plugin for name, plugin in discovered}

    rules_plugin = discovered_map["rules"]
    assert len(rules_plugin._rules) == 1
    assert rules_plugin._rules[0].name == "project rule"


def test_discover_plugins_merges_builtin_installed_and_local_with_precedence(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    builtin_rules = object()
    installed_rules = object()
    local_rules = object()
    builtin_only = object()
    installed_only = object()
    local_only = object()

    monkeypatch.setattr(
        discovery_module,
        "_discover_builtin",
        lambda rules_path=None: [("rules", builtin_rules), ("builtin-only", builtin_only)],
    )
    monkeypatch.setattr(
        discovery_module,
        "_discover_installed",
        lambda: [("rules", installed_rules), ("installed-only", installed_only)],
    )
    monkeypatch.setattr(
        discovery_module,
        "_discover_local",
        lambda: [("rules", local_rules), ("local-only", local_only)],
    )
    caplog.set_level("INFO")

    discovered = discover_plugins()
    discovered_map = {name: plugin for name, plugin in discovered}

    assert discovered_map == {
        "rules": local_rules,
        "builtin-only": builtin_only,
        "installed-only": installed_only,
        "local-only": local_only,
    }
    assert "Installed plugin 'rules' overrides builtin version" in caplog.text
    assert "Local plugin 'rules' overrides installed version" in caplog.text


def test_discover_local_supports_absolute_self_imports(tmp_path: Path) -> None:
    plugins_dir = tmp_path / "plugins"
    plugin_root = plugins_dir / "nomnom-plugin-abs"
    module_dir = plugin_root / "nomnom_plugin_abs"
    module_dir.mkdir(parents=True)

    (module_dir / "helper.py").write_text("VALUE = 'ok'\n")
    (module_dir / "__init__.py").write_text(
        "from nomnom_plugin_abs.helper import VALUE\n"
        "class AbsPlugin:\n"
        "    value = VALUE\n"
        "    def matches(self, event): return False\n"
        "    def handle(self, event): return []\n"
    )
    (plugin_root / "pyproject.toml").write_text(
        '[project]\nname = "nomnom-plugin-abs"\nversion = "0.1.0"\n\n'
        '[project.entry-points."nomnom.plugins"]\n'
        'abs = "nomnom_plugin_abs:AbsPlugin"\n'
    )

    discovered = _discover_local(plugins_dir)

    assert len(discovered) == 1
    name, plugin = discovered[0]
    assert name == "abs"
    assert plugin.value == "ok"


def test_discover_local_namespaces_absolute_imports_to_prevent_collision(
    tmp_path: Path,
) -> None:
    plugins_dir = tmp_path / "plugins"

    for plugin_name, class_name, tag in [
        ("nomnom-plugin-alpha", "AlphaPlugin", "alpha"),
        ("nomnom-plugin-beta", "BetaPlugin", "beta"),
    ]:
        plugin_root = plugins_dir / plugin_name
        module_dir = plugin_root / "nomnom_plugin_common"
        module_dir.mkdir(parents=True)
        (module_dir / "helper.py").write_text(f"TAG = '{tag}'\n")
        (module_dir / "__init__.py").write_text(
            "from nomnom_plugin_common.helper import TAG\n"
            f"class {class_name}:\n"
            "    tag = TAG\n"
            "    def matches(self, event): return False\n"
            "    def handle(self, event): return []\n"
        )
        (plugin_root / "pyproject.toml").write_text(
            f'[project]\nname = "{plugin_name}"\nversion = "0.1.0"\n\n'
            f'[project.entry-points."nomnom.plugins"]\n'
            f'{tag} = "nomnom_plugin_common:{class_name}"\n'
        )

    discovered = _discover_local(plugins_dir)

    assert len(discovered) == 2
    tags = {plugin.tag for _, plugin in discovered}
    assert tags == {"alpha", "beta"}


def test_discover_local_namespaces_modules_to_prevent_collision(tmp_path: Path) -> None:
    """Two plugins with the same internal module name must not collide in sys.modules."""
    plugins_dir = tmp_path / "plugins"

    for plugin_name, class_name, tag in [
        ("nomnom-plugin-alpha", "AlphaPlugin", "alpha"),
        ("nomnom-plugin-beta", "BetaPlugin", "beta"),
    ]:
        plugin_root = plugins_dir / plugin_name
        module_dir = plugin_root / "nomnom_plugin_common"
        module_dir.mkdir(parents=True)
        (module_dir / "__init__.py").write_text(
            f"class {class_name}:\n"
            f"    tag = '{tag}'\n"
            f"    def matches(self, event): return False\n"
            f"    def handle(self, event): return []\n"
        )
        (plugin_root / "pyproject.toml").write_text(
            f'[project]\nname = "{plugin_name}"\nversion = "0.1.0"\n\n'
            f'[project.entry-points."nomnom.plugins"]\n'
            f'{tag} = "nomnom_plugin_common:{class_name}"\n'
        )

    discovered = _discover_local(plugins_dir)

    assert len(discovered) == 2
    tags = {plugin.tag for _, plugin in discovered}
    assert tags == {"alpha", "beta"}


def test_discover_new_plugins_filters_known_plugins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invalidate_calls: list[bool] = []

    monkeypatch.setattr(
        discovery_module.importlib,
        "invalidate_caches",
        lambda: invalidate_calls.append(True),
    )
    monkeypatch.setattr(
        discovery_module,
        "_discover_builtin",
        lambda: (_ for _ in ()).throw(AssertionError("builtin discovery should not run")),
    )

    existing_plugin = object()
    new_plugin = object()
    monkeypatch.setattr(
        discovery_module,
        "_discover_installed",
        lambda: [("existing", existing_plugin), ("fresh", new_plugin)],
    )

    discovered = discover_new_plugins({"existing", "rules"})

    assert invalidate_calls == [True]
    assert discovered == [("fresh", new_plugin)]
