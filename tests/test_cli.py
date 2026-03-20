from types import SimpleNamespace
import sys

from typer.testing import CliRunner

import nomnom.cli as cli_module
from nomnom.cli import app


def test_watch_prompts_setup_when_default_config_missing() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["watch"])

    assert result.exit_code == 1
    assert "Config file not found: config.toml" in result.output
    assert "Run `nomnom setup` to create one." in result.output


def test_watch_dry_run_passes_flag(monkeypatch, tmp_path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[[watch]]
name = "inbox"
paths = ["./inbox"]
""".strip()
        + "\n"
    )

    captured_kwargs = {}
    runner = CliRunner()

    monkeypatch.setattr(cli_module, "discover_plugins", lambda: [])

    def fake_run_watcher(cfg, plugins, console, **kwargs):
        captured_kwargs.update(kwargs)

    monkeypatch.setattr(cli_module, "run_watcher", fake_run_watcher)

    result = runner.invoke(app, ["watch", "--config", str(config_path), "--dry"])

    assert result.exit_code == 0
    assert captured_kwargs.get("dry_run") is True


def test_watch_once_passes_flag(monkeypatch, tmp_path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[[watch]]
name = "inbox"
paths = ["./inbox"]
""".strip()
        + "\n"
    )

    captured_kwargs = {}
    runner = CliRunner()

    monkeypatch.setattr(cli_module, "discover_plugins", lambda: [])

    def fake_run_watcher(cfg, plugins, console, **kwargs):
        captured_kwargs.update(kwargs)

    monkeypatch.setattr(cli_module, "run_watcher", fake_run_watcher)

    result = runner.invoke(app, ["watch", "--config", str(config_path), "--once"])

    assert result.exit_code == 0
    assert captured_kwargs.get("once") is True


def test_watch_once_and_dry_run_combined(monkeypatch, tmp_path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[[watch]]
name = "inbox"
paths = ["./inbox"]
""".strip()
        + "\n"
    )

    captured_kwargs = {}
    runner = CliRunner()

    monkeypatch.setattr(cli_module, "discover_plugins", lambda: [])

    def fake_run_watcher(cfg, plugins, console, **kwargs):
        captured_kwargs.update(kwargs)

    monkeypatch.setattr(cli_module, "run_watcher", fake_run_watcher)

    result = runner.invoke(
        app,
        ["watch", "--config", str(config_path), "--once", "--dry-run"],
    )

    assert result.exit_code == 0
    assert captured_kwargs.get("once") is True
    assert captured_kwargs.get("dry_run") is True


def test_watch_once_with_group_passes_group_name(monkeypatch, tmp_path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[[watch]]
name = "inbox"
paths = ["./inbox"]

[[watch]]
name = "archive"
paths = ["./archive"]
""".strip()
        + "\n"
    )

    captured_kwargs = {}
    runner = CliRunner()

    monkeypatch.setattr(cli_module, "discover_plugins", lambda: [])

    def fake_run_watcher(cfg, plugins, console, **kwargs):
        captured_kwargs.update(kwargs)

    monkeypatch.setattr(cli_module, "run_watcher", fake_run_watcher)

    result = runner.invoke(app, ["watch", "--config", str(config_path), "--once", "archive"])

    assert result.exit_code == 0
    assert captured_kwargs.get("once") is True
    assert captured_kwargs.get("once_watch_group") == "archive"


def test_watch_group_name_requires_once(monkeypatch, tmp_path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[[watch]]
name = "inbox"
paths = ["./inbox"]
""".strip()
        + "\n"
    )

    runner = CliRunner()
    monkeypatch.setattr(cli_module, "discover_plugins", lambda: [])

    def fail_run_watcher(*_args, **_kwargs):
        raise AssertionError("run_watcher should not be called")

    monkeypatch.setattr(cli_module, "run_watcher", fail_run_watcher)

    result = runner.invoke(app, ["watch", "--config", str(config_path), "inbox"])

    assert result.exit_code == 1
    assert "Watch group argument is only supported with --once." in result.output


def test_watch_once_with_unknown_group_fails(monkeypatch, tmp_path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[[watch]]
name = "inbox"
paths = ["./inbox"]

[[watch]]
name = "archive"
paths = ["./archive"]
""".strip()
        + "\n"
    )

    runner = CliRunner()
    monkeypatch.setattr(cli_module, "discover_plugins", lambda: [])

    def fail_run_watcher(*_args, **_kwargs):
        raise AssertionError("run_watcher should not be called")

    monkeypatch.setattr(cli_module, "run_watcher", fail_run_watcher)

    result = runner.invoke(app, ["watch", "--config", str(config_path), "--once", "missing"])

    assert result.exit_code == 1
    assert "Watch group not found: missing" in result.output
    assert "Available groups: archive, inbox" in result.output


def test_plugin_install_runs_setup_for_new_plugin(
    monkeypatch,
) -> None:
    class PluginWithSetup:
        def __init__(self) -> None:
            self.setup_called = False

        def setup(self) -> None:
            self.setup_called = True

    plugin = PluginWithSetup()
    runner = CliRunner()
    seen_cmd = None

    def fake_run(cmd, *args, **kwargs):
        nonlocal seen_cmd
        seen_cmd = cmd
        return SimpleNamespace(returncode=0, stderr="", stdout="")

    monkeypatch.setattr(cli_module, "get_installed_plugin_names", lambda: {"existing"})
    monkeypatch.setattr(
        cli_module,
        "discover_new_plugins",
        lambda known_names: [("fresh", plugin)],
    )
    monkeypatch.setattr(
        "subprocess.run",
        fake_run,
    )

    result = runner.invoke(app, ["plugin", "add", "nomnom-plugin-fresh"])

    assert result.exit_code == 0
    assert plugin.setup_called is True
    assert seen_cmd == [
        "uv",
        "pip",
        "install",
        "--python",
        sys.executable,
        "--",
        "nomnom-plugin-fresh",
    ]
    assert "Running setup() for plugin 'fresh'..." in result.output
    assert "Setup completed for plugin 'fresh'." in result.output


def test_plugin_install_skips_setup_with_no_setup_flag(monkeypatch) -> None:
    runner = CliRunner()

    monkeypatch.setattr(cli_module, "get_installed_plugin_names", lambda: {"existing"})
    monkeypatch.setattr(
        cli_module,
        "discover_new_plugins",
        lambda known_names: [("fresh", object())],
    )
    monkeypatch.setattr(
        "subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stderr="", stdout=""),
    )

    result = runner.invoke(app, ["plugin", "add", "nomnom-plugin-fresh", "--no-setup"])

    assert result.exit_code == 0
    assert "Skipping plugin setup (--no-setup)" in result.output


def test_plugin_install_handles_setup_failure(monkeypatch) -> None:
    class PluginWithFailingSetup:
        def setup(self) -> None:
            raise RuntimeError("boom")

    runner = CliRunner()

    monkeypatch.setattr(cli_module, "get_installed_plugin_names", lambda: {"existing"})
    monkeypatch.setattr(
        cli_module,
        "discover_new_plugins",
        lambda known_names: [("fresh", PluginWithFailingSetup())],
    )
    monkeypatch.setattr(
        "subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stderr="", stdout=""),
    )

    result = runner.invoke(app, ["plugin", "add", "nomnom-plugin-fresh"])

    assert result.exit_code == 1
    assert "Setup failed for plugin 'fresh': boom" in result.output
    assert "One or more plugin setup steps failed." in result.output


def test_plugin_install_handles_keyboard_interrupt_during_setup(monkeypatch) -> None:
    class PluginWithInterruptedSetup:
        def setup(self) -> None:
            raise KeyboardInterrupt

    runner = CliRunner()

    monkeypatch.setattr(cli_module, "get_installed_plugin_names", lambda: {"existing"})
    monkeypatch.setattr(
        cli_module,
        "discover_new_plugins",
        lambda known_names: [("fresh", PluginWithInterruptedSetup())],
    )
    monkeypatch.setattr(
        "subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stderr="", stdout=""),
    )

    result = runner.invoke(app, ["plugin", "add", "nomnom-plugin-fresh"])

    assert result.exit_code == 1
    assert "Setup cancelled for plugin 'fresh'." in result.output


def test_plugin_install_handles_no_new_plugins(monkeypatch) -> None:
    runner = CliRunner()

    monkeypatch.setattr(cli_module, "get_installed_plugin_names", lambda: {"existing"})
    monkeypatch.setattr(cli_module, "discover_new_plugins", lambda known_names: [])
    monkeypatch.setattr(
        "subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stderr="", stdout=""),
    )

    result = runner.invoke(app, ["plugin", "add", "nomnom-plugin-fresh"])

    assert result.exit_code == 0
    assert "No new plugins detected after install; skipping setup." in result.output


def test_plugin_install_skips_plugin_without_setup(monkeypatch) -> None:
    class PluginWithoutSetup:
        def matches(self, event):
            return False

        def handle(self, event):
            return []

    runner = CliRunner()

    monkeypatch.setattr(cli_module, "get_installed_plugin_names", lambda: {"existing"})
    monkeypatch.setattr(
        cli_module,
        "discover_new_plugins",
        lambda known_names: [("fresh", PluginWithoutSetup())],
    )
    monkeypatch.setattr(
        "subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stderr="", stdout=""),
    )

    result = runner.invoke(app, ["plugin", "add", "nomnom-plugin-fresh"])

    assert result.exit_code == 0
    assert "Plugin 'fresh' has no setup() method; skipping." in result.output
    assert "No plugin setup was executed." in result.output


def test_plugin_install_handles_missing_uv(monkeypatch) -> None:
    runner = CliRunner()

    monkeypatch.setattr(cli_module, "get_installed_plugin_names", lambda: {"existing"})
    monkeypatch.setattr(
        "subprocess.run",
        lambda *args, **kwargs: (_ for _ in ()).throw(FileNotFoundError("uv")),
    )

    result = runner.invoke(app, ["plugin", "add", "nomnom-plugin-fresh"])

    assert result.exit_code == 1
    assert "Installation failed: could not execute 'uv'" in result.output


def test_plugin_setup_runs_named_plugin_setup(monkeypatch) -> None:
    class PluginWithSetup:
        def __init__(self) -> None:
            self.setup_called = False

        def setup(self) -> None:
            self.setup_called = True

    fresh = PluginWithSetup()
    runner = CliRunner()

    monkeypatch.setattr(
        cli_module,
        "discover_plugins",
        lambda: [("fresh", fresh), ("other", object())],
    )

    result = runner.invoke(app, ["plugin", "setup", "fresh"])

    assert result.exit_code == 0
    assert fresh.setup_called is True
    assert "Running setup() for plugin 'fresh'..." in result.output
    assert "Setup completed for plugin 'fresh'." in result.output


def test_plugin_setup_supports_all_flag(monkeypatch) -> None:
    class PluginWithSetup:
        def __init__(self) -> None:
            self.setup_called = False

        def setup(self) -> None:
            self.setup_called = True

    alpha = PluginWithSetup()
    beta = PluginWithSetup()
    runner = CliRunner()

    monkeypatch.setattr(
        cli_module,
        "discover_plugins",
        lambda: [("alpha", alpha), ("beta", beta)],
    )

    result = runner.invoke(app, ["plugin", "setup", "--all"])

    assert result.exit_code == 0
    assert alpha.setup_called is True
    assert beta.setup_called is True
    assert "Running setup() for plugin 'alpha'..." in result.output
    assert "Running setup() for plugin 'beta'..." in result.output


def test_plugin_setup_errors_when_plugin_is_missing(monkeypatch) -> None:
    runner = CliRunner()

    monkeypatch.setattr(
        cli_module,
        "discover_plugins",
        lambda: [("alpha", object())],
    )

    result = runner.invoke(app, ["plugin", "setup", "fresh"])

    assert result.exit_code == 1
    assert "Plugin 'fresh' was not found." in result.output


def test_plugin_setup_requires_name_or_all(monkeypatch) -> None:
    runner = CliRunner()

    monkeypatch.setattr(cli_module, "discover_plugins", lambda: [])

    result = runner.invoke(app, ["plugin", "setup"])

    assert result.exit_code == 1
    assert "Provide a plugin name or pass --all." in result.output


def test_plugin_setup_rejects_name_with_all(monkeypatch) -> None:
    runner = CliRunner()

    monkeypatch.setattr(cli_module, "discover_plugins", lambda: [])

    result = runner.invoke(app, ["plugin", "setup", "fresh", "--all"])

    assert result.exit_code == 1
    assert "Choose either a plugin name or --all, not both." in result.output
